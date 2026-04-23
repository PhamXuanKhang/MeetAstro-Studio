"""
Celery task: analyze transcript → tạo analysis + review_items.

Input:  meeting_id (str), transcript_id (str)
Output: {"analysis_id": str, "review_item_count": int, "flagged_count": int}
"""
import asyncio
import uuid

from src.config import get_logger
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
    """Phân tích transcript bằng GPT-4o và tạo review items."""
    return asyncio.run(_analyze_async(self, meeting_id, transcript_id))


async def _analyze_async(task, meeting_id: str, transcript_id: str) -> dict:
    from src.config import get_settings
    from src.db.crud.meeting_crud import (
        create_analysis_result,
        get_transcript,
        update_meeting_status,
    )
    from src.db.crud.review_crud import bulk_create_review_items, delete_review_items_for_meeting
    from src.db.session import get_session_factory
    from src.services.analysis_service import analyze_async

    session_factory = get_session_factory()

    meeting_uuid = uuid.UUID(meeting_id)
    settings = get_settings()

    async with session_factory() as db:
        await update_meeting_status(db, meeting_uuid, status="analyzing")
        await db.commit()

    # Lấy transcript text
    async with session_factory() as db:
        transcript = await get_transcript(db, meeting_uuid)
        if not transcript:
            raise ValueError(f"Transcript {transcript_id} không tồn tại.")
        transcript_text = transcript.raw_text

    if not transcript_text.strip():
        async with session_factory() as db:
            await update_meeting_status(
                db, meeting_uuid, status="failed", error_message="Transcript is empty — cannot analyze."
            )
            await db.commit()
        raise ValueError("Transcript is empty — cannot analyze.")

    try:
        logger.info(f"[analyze_task] Starting analysis for meeting {meeting_id}")
        meeting_analysis = await analyze_async(transcript_text)
    except Exception as exc:
        async with session_factory() as db:
            await update_meeting_status(
                db, meeting_uuid, status="failed", error_message=str(exc)
            )
            await db.commit()
        raise task.retry(exc=exc)

    # Tính overall_confidence
    all_confidences = []
    for epic in meeting_analysis.epics:
        for task_item in epic.tasks:
            all_confidences.append(task_item.confidence)
            for sub in task_item.subtasks:
                all_confidences.append(sub.confidence)
    overall_conf = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0

    # Lưu analysis_result + review_items
    async with session_factory() as db:
        analysis_result = await create_analysis_result(
            db,
            meeting_id=meeting_uuid,
            analysis_json=meeting_analysis.to_dict(),
            summary=meeting_analysis.summary,
            overall_confidence=overall_conf,
        )

        # Remove stale review items from any previous analysis run
        await delete_review_items_for_meeting(db, meeting_uuid)

        # Flatten Epic/Task/Subtask → review_items
        review_items_data = _flatten_to_review_items(
            meeting_analysis, str(meeting_uuid), settings.confidence_low_threshold
        )
        if review_items_data:
            await bulk_create_review_items(db, review_items_data)

        flagged_count = sum(1 for i in review_items_data if i["is_flagged"])
        await update_meeting_status(db, meeting_uuid, status="draft")
        await db.commit()

    logger.info(
        f"[analyze_task] Xong: analysis_id={analysis_result.id} "
        f"items={len(review_items_data)} flagged={flagged_count}"
    )
    return {
        "analysis_id": str(analysis_result.id),
        "review_item_count": len(review_items_data),
        "flagged_count": flagged_count,
    }


def _priority_str(priority_val) -> str:
    return priority_val.value if hasattr(priority_val, "value") else str(priority_val)


def _flatten_to_review_items(
    analysis, meeting_id: str, low_threshold: float
) -> list[dict]:
    """Chuyển MeetingAnalysis thành list dicts để bulk insert vào review_items."""
    items = []
    for epic_idx, epic in enumerate(analysis.epics):
        # Epic item
        items.append({
            "meeting_id": uuid.UUID(meeting_id),
            "item_type": "epic",
            "item_index": str(epic_idx),
            "summary": epic.summary,
            "context": epic.description,
            "confidence": 1.0,
            "is_flagged": False,
        })
        for task_idx, task in enumerate(epic.tasks):
            items.append({
                "meeting_id": uuid.UUID(meeting_id),
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
                    "meeting_id": uuid.UUID(meeting_id),
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
