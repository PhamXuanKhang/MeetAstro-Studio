"""
Analysis service - orchestrate parallel summary + AI extraction + validation.
"""
from __future__ import annotations

import asyncio
from typing import Any

from src.config import get_logger, get_settings
from src.providers.mock_analyzer import MockAnalyzer
from src.providers.openai_analyzer import OpenAIAnalyzer
from src.schema import Epic, MeetingAnalysis, Priority, Subtask, Task
from src.services.extraction_service import rule_based_extraction
from src.services.status_update_service import format_status_candidates_for_prompt
from src.services.summarization_service import generate_summary
from src.services.validation_service import validate_action_items

logger = get_logger(__name__)

_PRIORITY_MAP = {
    "critical": Priority.CRITICAL,
    "high": Priority.HIGH,
    "medium": Priority.MEDIUM,
    "low": Priority.LOW,
}


def _get_priority_str(priority: Priority) -> str:
    """Extract priority value as lowercase string."""
    if hasattr(priority, "value"):
        return priority.value.lower()
    return str(priority).lower()


def _build_analysis_source(
    source_text: str,
    status_candidates: list[dict[str, Any]] | None,
) -> str:
    if not status_candidates:
        return source_text

    return (
        "SOURCE MEETING CONTENT:\n"
        f"{source_text}\n\n"
        "OPEN WORK STATUS CANDIDATES:\n"
        "The following existing task/subtask rows may be mentioned as completed, blocked, "
        "cancelled, or in progress. If the meeting clearly updates one of them, return it "
        "under status_updates using only one of these candidate ids. Do not recreate that "
        "same item as a new action item.\n"
        f"{format_status_candidates_for_prompt(status_candidates)}"
    )


def _extract_via_openai(
    transcript: str,
    status_candidates: list[dict[str, Any]] | None = None,
) -> MeetingAnalysis:
    """Call OpenAIAnalyzer synchronously."""
    analyzer = OpenAIAnalyzer()
    return analyzer.analyze(
        _build_analysis_source(transcript, status_candidates),
        language_source_text=transcript,
    )


def _analysis_to_items(analysis: MeetingAnalysis) -> list[dict[str, Any]]:
    items = []
    for epic in analysis.epics:
        for task in epic.tasks:
            items.append({
                "title": task.summary,
                "description": task.context,
                "assignee": task.assignee or "Unassigned",
                "deadline": task.deadline or "",
                "priority": _get_priority_str(task.priority),
                "context": task.context,
                "_epic_summary": epic.summary,
                "_epic_description": epic.description,
                "_subtasks": [
                    {
                        "title": s.summary,
                        "description": s.context,
                        "assignee": s.assignee or "Unassigned",
                        "deadline": s.deadline or "",
                        "priority": _get_priority_str(s.priority),
                        "context": s.context,
                    }
                    for s in task.subtasks
                ],
            })
    return items


def _format_synced_items(synced_items: list[dict[str, Any]]) -> str:
    if not synced_items:
        return "None."
    lines = []
    for item in synced_items:
        title = item.get("title") or ""
        jira_key = item.get("jira_issue_key") or "synced"
        item_type = item.get("item_type") or "item"
        description = item.get("description") or item.get("context") or ""
        lines.append(f"- [{item_type}] {title} ({jira_key})")
        if description:
            lines.append(f"  Context: {description}")
    return "\n".join(lines)


def analyze_note_actions(
    meeting_note: str,
    *,
    synced_items: list[dict[str, Any]] | None = None,
    status_candidates: list[dict[str, Any]] | None = None,
) -> MeetingAnalysis:
    """Extract action items from an edited meeting note without rewriting the note."""
    if not meeting_note.strip():
        raise ValueError("Meeting note cannot be empty.")

    settings = get_settings()
    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY empty - using MockAnalyzer for meeting note.")
        return MockAnalyzer().analyze(meeting_note)

    synced_context = _format_synced_items(synced_items or [])
    prompt = (
        "SOURCE TYPE: Curated meeting note.\n\n"
        "Task: Extract the action-item hierarchy and any status update proposals from this meeting note. "
        "Do not rewrite or summarize the meeting note itself. "
        "Do not recreate action items that are already synced to Jira.\n"
        "Priority order for source material: "
        "1) user-edited meeting note and action plan draft, "
        "2) current structured action plan if no draft exists, "
        "3) supporting transcript context only for missing details. "
        "If sources conflict, prefer the edited note/action plan draft.\n\n"
        "Already synced Jira items to skip:\n"
        f"{synced_context}\n\n"
        "Meeting note:\n"
        f"{meeting_note}\n\n"
        "Open work status candidates:\n"
        f"{format_status_candidates_for_prompt(status_candidates or [])}"
    )
    return OpenAIAnalyzer().analyze(prompt, language_source_text=meeting_note)


def _build_analysis(
    validated_items: list[dict[str, Any]],
    summary_result: dict[str, Any],
) -> MeetingAnalysis:
    """Reconstruct MeetingAnalysis from validated items + summary result."""
    epics_map: dict[str, Epic] = {}

    for item in validated_items:
        epic_summary = item.get("_epic_summary", "General")
        epic_desc = item.get("_epic_description", "")
        if epic_summary not in epics_map:
            epics_map[epic_summary] = Epic(summary=epic_summary, description=epic_desc)

        priority_str = item.get("priority", "medium").lower()
        priority = _PRIORITY_MAP.get(priority_str, Priority.MEDIUM)

        subtasks = []
        for sub in item.get("_subtasks", []):
            sub_priority = _PRIORITY_MAP.get(sub.get("priority", "medium").lower(), Priority.MEDIUM)
            subtasks.append(Subtask(
                summary=sub.get("title", ""),
                assignee=sub.get("assignee") or None,
                deadline=sub.get("deadline") or None,
                priority=sub_priority,
                context=sub.get("context", ""),
                confidence=item.get("confidence", 0.0),
                validation_notes=item.get("validation_notes", []),
            ))

        task = Task(
            summary=item.get("title", ""),
            assignee=item.get("assignee") or None,
            deadline=item.get("deadline") or None,
            priority=priority,
            context=item.get("context", ""),
            subtasks=subtasks,
            confidence=item.get("confidence", 0.0),
            validation_notes=item.get("validation_notes", []),
        )
        epics_map[epic_summary].tasks.append(task)

    return MeetingAnalysis(
        epics=list(epics_map.values()),
        summary=summary_result.get("summary", ""),
        key_decisions=summary_result.get("key_decisions", []),
        discussion_points=summary_result.get("discussion_points", []),
        parking_lot=summary_result.get("parking_lot_items", []),
    )


async def analyze_async(
    transcript: str,
    *,
    status_candidates: list[dict[str, Any]] | None = None,
) -> MeetingAnalysis:
    """
    Async core: run summary + AI extraction in parallel, validate, build result.

    Raises ValueError for empty transcript.
    Falls back to MockAnalyzer when OPENAI_API_KEY is empty.
    """
    if not transcript.strip():
        raise ValueError("Transcript cannot be empty.")

    settings = get_settings()
    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY empty - using MockAnalyzer.")
        return MockAnalyzer().analyze(transcript)

    loop = asyncio.get_event_loop()

    summary_coro = generate_summary(transcript)
    ai_extract_future = loop.run_in_executor(
        None,
        _extract_via_openai,
        transcript,
        status_candidates,
    )

    summary_result, ai_analysis = await asyncio.gather(summary_coro, ai_extract_future)
    ai_items = _analysis_to_items(ai_analysis)

    rule_items = rule_based_extraction(transcript)
    validated, metrics = validate_action_items(ai_items, rule_items, transcript)

    logger.info(
        "Validation metrics: overall=%.3f cross=%.3f context=%.3f structural=%.3f",
        metrics["overall_confidence"],
        metrics["cross_validation_score"],
        metrics["context_coherence_score"],
        metrics["structural_validation_score"],
    )

    analysis = _build_analysis(validated, summary_result)
    analysis.status_updates = ai_analysis.status_updates
    logger.info(
        "Analysis complete: %d epics, %d tasks.",
        len(analysis.epics),
        sum(len(e.tasks) for e in analysis.epics),
    )
    return analysis


def analyze(
    transcript: str,
    *,
    status_candidates: list[dict[str, Any]] | None = None,
) -> MeetingAnalysis:
    """
    Sync wrapper for UI / scripts that run outside an event loop.

    Use analyze_async() when already inside an event loop (e.g. Celery async tasks).
    Falls back to MockAnalyzer when OPENAI_API_KEY is empty.
    """
    if not transcript.strip():
        raise ValueError("Transcript cannot be empty.")

    settings = get_settings()
    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY empty - using MockAnalyzer.")
        return MockAnalyzer().analyze(transcript)

    return asyncio.run(analyze_async(transcript, status_candidates=status_candidates))
