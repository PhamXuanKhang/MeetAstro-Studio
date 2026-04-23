"""
Async CRUD cho Meeting, Transcript, AnalysisResult.

Tất cả hàm nhận AsyncSession từ FastAPI dependency injection.
"""
import uuid
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.models import AnalysisResult, Meeting, Transcript


async def create_meeting(
    db: AsyncSession,
    *,
    title: str,
    audio_path: Optional[str] = None,
    user_id: str = "default_user",
) -> Meeting:
    """Tạo meeting mới với trạng thái pending."""
    meeting = Meeting(title=title, audio_path=audio_path, user_id=user_id)
    db.add(meeting)
    await db.flush()
    await db.refresh(meeting)
    return meeting


async def get_meeting(
    db: AsyncSession, meeting_id: uuid.UUID, *, load_relations: bool = False
) -> Optional[Meeting]:
    """Lấy meeting theo ID. load_relations=True để load transcript + analysis."""
    stmt = select(Meeting).where(Meeting.id == meeting_id)
    if load_relations:
        stmt = stmt.options(
            selectinload(Meeting.transcript),
            selectinload(Meeting.analysis),
        )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_meetings(
    db: AsyncSession,
    *,
    user_id: str = "default_user",
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Meeting], int]:
    """Lấy danh sách meetings, trả về (items, total)."""
    from sqlalchemy import func

    base_stmt = select(Meeting).where(Meeting.user_id == user_id)
    if status:
        base_stmt = base_stmt.where(Meeting.status == status)

    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    stmt = (
        base_stmt.order_by(Meeting.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    return result.scalars().all(), total


async def update_meeting_status(
    db: AsyncSession,
    meeting_id: uuid.UUID,
    *,
    status: str,
    celery_task_id: Optional[str] = None,
    error_message: Optional[str] = None,
) -> None:
    """Cập nhật status và celery_task_id."""
    values: dict = {"status": status}
    if celery_task_id is not None:
        values["celery_task_id"] = celery_task_id
    if error_message is not None:
        values["error_message"] = error_message
    await db.execute(update(Meeting).where(Meeting.id == meeting_id).values(**values))


async def delete_meeting(db: AsyncSession, meeting_id: uuid.UUID) -> bool:
    """Xóa meeting và cascade xóa transcript, analysis, review_items."""
    meeting = await get_meeting(db, meeting_id)
    if not meeting:
        return False
    await db.delete(meeting)
    return True


async def create_transcript(
    db: AsyncSession,
    *,
    meeting_id: uuid.UUID,
    raw_text: str,
    diarized_text: Optional[str] = None,
    language: str = "en",
) -> Transcript:
    """Lưu transcript sau khi transcribe xong."""
    transcript = Transcript(
        meeting_id=meeting_id,
        raw_text=raw_text,
        diarized_text=diarized_text,
        language=language,
        char_count=len(raw_text),
    )
    db.add(transcript)
    await db.flush()
    await db.refresh(transcript)
    return transcript


async def get_transcript(
    db: AsyncSession, meeting_id: uuid.UUID
) -> Optional[Transcript]:
    """Lấy transcript của meeting."""
    result = await db.execute(
        select(Transcript).where(Transcript.meeting_id == meeting_id)
    )
    return result.scalar_one_or_none()


async def create_analysis_result(
    db: AsyncSession,
    *,
    meeting_id: uuid.UUID,
    analysis_json: dict,
    summary: Optional[str] = None,
    overall_confidence: Optional[float] = None,
    validation_metrics: Optional[dict] = None,
) -> AnalysisResult:
    """Upsert analysis result — update if one already exists for the meeting."""
    existing = await db.execute(
        select(AnalysisResult).where(AnalysisResult.meeting_id == meeting_id)
    )
    result = existing.scalar_one_or_none()
    if result is not None:
        result.analysis_json = analysis_json
        result.summary = summary
        result.overall_confidence = overall_confidence
        result.validation_metrics = validation_metrics
    else:
        result = AnalysisResult(
            meeting_id=meeting_id,
            analysis_json=analysis_json,
            summary=summary,
            overall_confidence=overall_confidence,
            validation_metrics=validation_metrics,
        )
        db.add(result)
    await db.flush()
    await db.refresh(result)
    return result


async def get_analysis_result(
    db: AsyncSession, meeting_id: uuid.UUID
) -> Optional[AnalysisResult]:
    """Lấy analysis result của meeting."""
    result = await db.execute(
        select(AnalysisResult).where(AnalysisResult.meeting_id == meeting_id)
    )
    return result.scalar_one_or_none()
