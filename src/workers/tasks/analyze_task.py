"""
Celery task: analyze transcript and create analysis + action_items.

Input:  meeting_id (str), transcript_id (str)
Output: {"analysis_id": str, "review_item_count": int, "flagged_count": int}
"""
from __future__ import annotations

import re
from typing import Any

from src.config import get_logger, get_settings
from src.db.crud.meeting_crud import (
    create_analysis_result,
    get_analysis_result,
    get_transcript_text,
    update_meeting_status,
)
from src.db.crud.review_crud import (
    bulk_create_review_items,
    delete_non_synced_review_items_for_meeting,
    list_review_items,
    list_synced_review_items,
    update_review_item_parent,
)
from src.workers.celery_app import celery_app

logger = get_logger(__name__)

_NON_WORD_RE = re.compile(r"[^\w\s]+", re.UNICODE)


@celery_app.task(
    name="analyze_transcript",
    bind=True,
    max_retries=1,
    default_retry_delay=10,
    queue="default",
)
def analyze_transcript(self, meeting_id: str, transcript_id: str) -> dict:
    """Analyze transcript using GPT-4o and create review items."""
    settings = get_settings()

    try:
        update_meeting_status(meeting_id, status="analyzing")
    except Exception as exc:
        logger.error("[analyze_task] Failed to update status: %s", exc)

    transcript_text = get_transcript_text(meeting_id)
    if not transcript_text.strip():
        update_meeting_status(
            meeting_id, status="failed",
            error_message="Transcript is empty - cannot analyze."
        )
        raise ValueError("Transcript is empty - cannot analyze.")

    try:
        logger.info(
            "[analyze_task] Starting analysis for meeting %s", meeting_id
        )
        from src.services.analysis_service import analyze
        meeting_analysis = analyze(transcript_text)
    except Exception as exc:
        update_meeting_status(
            meeting_id, status="failed", error_message=str(exc)
        )
        raise self.retry(exc=exc)

    all_confidences = []
    for epic in meeting_analysis.epics:
        for task_item in epic.tasks:
            all_confidences.append(task_item.confidence)
            for sub in task_item.subtasks:
                all_confidences.append(sub.confidence)
    overall_conf = (
        sum(all_confidences) / len(all_confidences) if all_confidences else 0.0
    )

    synced_items = list_synced_review_items(meeting_id)

    review_items_data = _flatten_to_review_items(
        meeting_analysis,
        meeting_id,
        settings.confidence_low_threshold,
        synced_items=synced_items,
    )

    # Delete only non-synced review items. Synced Jira items stay immutable.
    delete_non_synced_review_items_for_meeting(meeting_id)

    inserted: list[dict] = []
    if review_items_data:
        inserted = _insert_review_items_with_parents(review_items_data)

    # Upsert analysis result
    analysis_result = create_analysis_result(
        meeting_id=meeting_id,
        analysis_json=meeting_analysis.to_dict(),
        summary=meeting_analysis.summary,
        overall_confidence=overall_conf,
    )

    flagged_count = sum(1 for i in review_items_data if i.get("is_selected"))
    update_meeting_status(meeting_id, status="draft")

    logger.info(
        "[analyze_task] Complete: analysis_id=%s items=%d flagged=%d",
        analysis_result.get("id"),
        len(review_items_data),
        flagged_count,
    )
    return {
        "analysis_id": str(analysis_result.get("id")),
        "review_item_count": len(review_items_data),
        "flagged_count": flagged_count,
    }


@celery_app.task(
    name="regenerate_action_items_from_note",
    bind=True,
    max_retries=1,
    default_retry_delay=10,
    queue="default",
)
def regenerate_action_items_from_note(self, meeting_id: str) -> dict:
    """Regenerate non-synced action items from the editable meeting note."""
    settings = get_settings()

    try:
        update_meeting_status(meeting_id, status="analyzing")
    except Exception as exc:
        logger.error("[analyze_task] Failed to update status: %s", exc)

    analysis_result = get_analysis_result(meeting_id)
    if not analysis_result:
        update_meeting_status(
            meeting_id,
            status="failed",
            error_message="Analysis result is missing - cannot refresh action items.",
        )
        raise ValueError("Analysis result is missing - cannot refresh action items.")

    current_items = list_review_items(meeting_id)
    note_text = _analysis_result_to_note_text(analysis_result, current_items)
    if not note_text.strip():
        update_meeting_status(
            meeting_id,
            status="failed",
            error_message="Meeting note is empty - cannot refresh action items.",
        )
        raise ValueError("Meeting note is empty - cannot refresh action items.")

    synced_items = list_synced_review_items(meeting_id)

    try:
        from src.services.analysis_service import analyze_note_actions
        meeting_analysis = analyze_note_actions(note_text, synced_items=synced_items)
    except Exception as exc:
        update_meeting_status(meeting_id, status="failed", error_message=str(exc))
        raise self.retry(exc=exc)

    review_items_data = _flatten_to_review_items(
        meeting_analysis,
        meeting_id,
        settings.confidence_low_threshold,
        synced_items=synced_items,
    )

    delete_non_synced_review_items_for_meeting(meeting_id)
    inserted = _insert_review_items_with_parents(review_items_data)
    update_meeting_status(meeting_id, status="draft")

    logger.info(
        "[analyze_task] Refreshed action items from note: items=%d synced_kept=%d",
        len(inserted),
        len(synced_items),
    )
    return {
        "review_item_count": len(inserted),
        "synced_items_kept": len(synced_items),
    }


def _priority_str(priority_val) -> str:
    """Extract priority value as string."""
    return (
        priority_val.value
        if hasattr(priority_val, "value")
        else str(priority_val)
    )


def _sanitize_for_db(value: str | None) -> str | None:
    """
    Convert 'null' string to None to prevent PostgreSQL date parsing errors.

    Supabase SDK may serialize Python None as string "null" instead of SQL NULL,
    causing 'invalid input syntax for type date: "null"' errors.
    """
    if value is None or value == "" or value.lower() == "null":
        return None
    return value


def _normalize_title(title: str | None) -> str:
    normalized = _NON_WORD_RE.sub(" ", (title or "").lower())
    return " ".join(normalized.split())


def _synced_lookup_by_type(
    synced_items: list[dict[str, Any]],
) -> dict[tuple[str, str], dict[str, Any]]:
    lookup: dict[tuple[str, str], dict[str, Any]] = {}
    for item in synced_items:
        title = _normalize_title(item.get("title"))
        item_type = item.get("item_type")
        if title and item_type:
            lookup[(str(item_type), title)] = item
    return lookup


def _items_to_action_plan_text(items: list[dict[str, Any]]) -> str:
    if not items:
        return ""

    lines: list[str] = []
    for item in items:
        item_type = str(item.get("item_type") or "task").upper()
        title = item.get("title") or ""
        if not title:
            continue
        assignee = item.get("assignee")
        priority = item.get("priority")
        deadline = item.get("deadline")
        description = item.get("description") or item.get("context")

        meta = []
        if assignee:
            meta.append(f"assignee: {assignee}")
        if priority:
            meta.append(f"priority: {priority}")
        if deadline:
            meta.append(f"due: {deadline}")
        suffix = f" ({'; '.join(meta)})" if meta else ""
        lines.append(f"- [{item_type}] {title}{suffix}")
        if description:
            lines.append(f"  Context: {description}")
    return "\n".join(lines)


def _analysis_result_to_note_text(
    result: dict[str, Any],
    current_items: list[dict[str, Any]] | None = None,
) -> str:
    raw = result.get("raw_response") or {}
    if not isinstance(raw, dict):
        raw = {}

    sections: list[str] = []
    summary = result.get("summary_text") or raw.get("summary")
    if summary:
        sections.append(f"Insight:\n{summary}")

    discussion = raw.get("discussion_points") or raw.get("insights") or []
    if isinstance(discussion, list) and discussion:
        sections.append("Discussion points:\n" + "\n".join(f"- {x}" for x in discussion))

    decisions = result.get("key_decisions") or raw.get("key_decisions") or []
    if isinstance(decisions, list) and decisions:
        sections.append("Key decisions:\n" + "\n".join(f"- {x}" for x in decisions))

    parking = result.get("parking_lot") or raw.get("parking_lot_items") or raw.get("parking_lot") or []
    if isinstance(parking, list) and parking:
        sections.append("Parking lot:\n" + "\n".join(f"- {x}" for x in parking))

    action_plan_draft = raw.get("action_plan_draft")
    if isinstance(action_plan_draft, str) and action_plan_draft.strip():
        sections.append("User-edited action plan draft:\n" + action_plan_draft.strip())
    else:
        action_plan_text = _items_to_action_plan_text(current_items or [])
        if action_plan_text:
            sections.append("Current structured action plan:\n" + action_plan_text)

    transcript_text = get_transcript_text(result.get("meeting_id", ""))
    if transcript_text.strip():
        sections.append(
            "Supporting transcript context:\n"
            "Use this only to fill missing names, rationale, deadlines, or context. "
            "If it conflicts with the edited meeting note or action plan draft, prefer the edited note/draft.\n"
            f"{transcript_text}"
        )

    return "\n\n".join(sections)


def _make_row_key(item_type: str, title: str, index: int) -> str:
    return f"{item_type}:{index}:{_normalize_title(title)}"


def _flatten_to_review_items(
    analysis,
    meeting_id: str,
    low_threshold: float,
    *,
    synced_items: list[dict[str, Any]] | None = None,
) -> list[dict]:
    """
    Convert MeetingAnalysis to list of dicts for bulk insert into action_items.

    Column mapping to action_items:
      - summary       → title
      - is_flagged    → is_selected  (inverted: flagged=False → selected=True)
      - item_index    → (removed — not available in action_items schema)
      - edited_*      → (removed — edits go directly to title/assignee/deadline/priority)

    parent_id is set in a second pass after IDs are generated by the DB insert.
    """
    items: list[dict] = []
    synced_items = synced_items or []
    synced_lookup = _synced_lookup_by_type(synced_items)
    row_index = 0

    for epic in analysis.epics:
        epic_title = epic.summary
        epic_existing = synced_lookup.get(("epic", _normalize_title(epic_title)))
        epic_key = _make_row_key("epic", epic_title, row_index)
        if epic_existing:
            epic_parent_id = epic_existing.get("id")
        else:
            epic_parent_id = None
            items.append({
                "_key": epic_key,
                "meeting_id": meeting_id,
                "item_type": "epic",
                "title": epic_title,
                "description": epic.description,
                "review_status": "draft",
                "is_selected": False,
            })
            row_index += 1
        for task in epic.tasks:
            task_title = task.summary
            task_existing = synced_lookup.get(("task", _normalize_title(task_title)))
            task_key = _make_row_key("task", task_title, row_index)
            if task_existing:
                task_parent_id = (task_existing or {}).get("id")
            else:
                task_parent_id = None
                task_row: dict[str, Any] = {
                    "_key": task_key,
                    "meeting_id": meeting_id,
                    "item_type": "task",
                    "parent_id": epic_parent_id,
                    "title": task_title,
                    "assignee": task.assignee,
                    "deadline": _sanitize_for_db(task.deadline),
                    "priority": _priority_str(task.priority),
                    "description": task.context,
                    "confidence_score": task.confidence,
                    "review_status": "draft",
                    "is_selected": task.confidence < low_threshold,
                }
                if not epic_parent_id and not epic_existing:
                    task_row["_parent_key"] = epic_key
                items.append(task_row)
                row_index += 1
            for sub in task.subtasks:
                sub_title = sub.summary
                if synced_lookup.get(("subtask", _normalize_title(sub_title))):
                    continue
                sub_row: dict[str, Any] = {
                    "_key": _make_row_key("subtask", sub_title, row_index),
                    "meeting_id": meeting_id,
                    "item_type": "subtask",
                    "parent_id": task_parent_id,
                    "title": sub_title,
                    "assignee": sub.assignee,
                    "deadline": _sanitize_for_db(sub.deadline),
                    "priority": _priority_str(sub.priority),
                    "description": sub.context,
                    "confidence_score": sub.confidence,
                    "review_status": "draft",
                    "is_selected": sub.confidence < low_threshold,
                }
                if not task_parent_id and not task_existing:
                    sub_row["_parent_key"] = task_key
                items.append(sub_row)
                row_index += 1

    return items


def _insert_review_items_with_parents(items: list[dict[str, Any]]) -> list[dict]:
    if not items:
        return []

    keys = [item.get("_key") for item in items]
    parent_keys = [item.get("_parent_key") for item in items]
    rows = [
        {key: value for key, value in item.items() if not key.startswith("_")}
        for item in items
    ]
    inserted = bulk_create_review_items(rows)
    key_to_id = {
        str(key): inserted[idx]["id"]
        for idx, key in enumerate(keys)
        if key and idx < len(inserted)
    }

    for idx, parent_key in enumerate(parent_keys):
        if not parent_key or idx >= len(inserted):
            continue
        parent_id = key_to_id.get(str(parent_key))
        if parent_id:
            update_review_item_parent(inserted[idx]["id"], parent_id)
            inserted[idx]["parent_id"] = parent_id

    return inserted
