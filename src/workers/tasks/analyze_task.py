"""
Celery task: analyze transcript and create analysis + review_items.

Input:  meeting_id (str), transcript_id (str)
Output: {"analysis_id": str, "review_item_count": int, "flagged_count": int}
"""
from src.config import get_logger, get_settings
from src.db.crud.meeting_crud import (
    create_analysis_result,
    get_transcript,
    update_meeting_status,
)
from src.db.crud.review_crud import (
    bulk_create_review_items,
    delete_review_items_for_meeting,
)
from src.workers.celery_app import celery_app

logger = get_logger(__name__)


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

    transcript = get_transcript(meeting_id)
    if not transcript:
        raise ValueError(f"Transcript {transcript_id} does not exist.")

    transcript_text = transcript.get("raw_text", "")
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

    # Delete old review items
    delete_review_items_for_meeting(meeting_id)

    review_items_data = _flatten_to_review_items(
        meeting_analysis, meeting_id, settings.confidence_low_threshold
    )

    if review_items_data:
        bulk_create_review_items(review_items_data)

    # Upsert analysis result
    analysis_result = create_analysis_result(
        meeting_id=meeting_id,
        analysis_json=meeting_analysis.to_dict(),
        summary=meeting_analysis.summary,
        overall_confidence=overall_conf,
    )

    flagged_count = sum(1 for i in review_items_data if i.get("is_flagged"))
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


def _priority_str(priority_val) -> str:
    """Extract priority value as string."""
    return (
        priority_val.value
        if hasattr(priority_val, "value")
        else str(priority_val)
    )


def _flatten_to_review_items(
    analysis, meeting_id: str, low_threshold: float
) -> list[dict]:
    """Convert MeetingAnalysis to list of dicts for bulk insert."""
    items = []
    for epic_idx, epic in enumerate(analysis.epics):
        items.append({
            "meeting_id": meeting_id,
            "item_type": "epic",
            "item_index": str(epic_idx),
            "summary": epic.summary,
            "context": epic.description,
            "confidence": 1.0,
            "is_flagged": False,
        })
        for task_idx, task in enumerate(epic.tasks):
            items.append({
                "meeting_id": meeting_id,
                "item_type": "task",
                "item_index": f"{epic_idx}.{task_idx}",
                "summary": task.summary,
                "assignee": task.assignee,
                "deadline": task.deadline,
                "priority": _priority_str(task.priority),
                "context": task.context,
                "confidence": task.confidence,
                "is_flagged": task.confidence < low_threshold,
                "validation_notes": task.validation_notes,
            })
            for sub_idx, sub in enumerate(task.subtasks):
                items.append({
                    "meeting_id": meeting_id,
                    "item_type": "subtask",
                    "item_index": f"{epic_idx}.{task_idx}.{sub_idx}",
                    "summary": sub.summary,
                    "assignee": sub.assignee,
                    "deadline": sub.deadline,
                    "priority": _priority_str(sub.priority),
                    "context": sub.context,
                    "confidence": sub.confidence,
                    "is_flagged": sub.confidence < low_threshold,
                    "validation_notes": sub.validation_notes,
                })
    return items
