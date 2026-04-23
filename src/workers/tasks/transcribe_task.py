"""
Celery task: transcribe audio file → lưu transcript vào DB.

Input:  meeting_id (str), audio_path (str), diarize (bool), language (str)
Output: {"transcript_id": str, "char_count": int}
"""
import asyncio
import uuid

from src.config import get_logger
from src.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(
    name="transcribe_audio",
    bind=True,
    max_retries=2,
    default_retry_delay=5,
    queue="default",
)
def transcribe_audio(
    self,
    meeting_id: str,
    audio_path: str,
    *,
    diarize: bool = False,
    language: str = "en",
) -> dict:
    """Transcribe audio và lưu vào bảng transcripts."""
    return asyncio.run(_transcribe_async(self, meeting_id, audio_path, diarize, language))


async def _transcribe_async(
    task, meeting_id: str, audio_path: str, diarize: bool, language: str
) -> dict:
    from src.db.session import get_session_factory
    from src.db.crud.meeting_crud import (
        create_transcript,
        get_transcript,
        update_meeting_status,
    )
    from src.services.transcription_service import transcribe, transcribe_diarized

    session_factory = get_session_factory()

    meeting_uuid = uuid.UUID(meeting_id)
    async with session_factory() as db:
        try:
            await update_meeting_status(db, meeting_uuid, status="transcribing")
            await db.commit()
        except Exception as exc:
            logger.error(f"[transcribe_task] Lỗi cập nhật status: {exc}")
            raise

    try:
        logger.info(f"[transcribe_task] Bắt đầu transcribe: {audio_path} diarize={diarize}")
        if diarize:
            raw_text = transcribe_diarized(audio_path, language=language)
            diarized_text = raw_text
        else:
            raw_text = transcribe(audio_path, language=language)
            diarized_text = None
    except Exception as exc:
        async with session_factory() as db:
            await update_meeting_status(
                db, meeting_uuid, status="failed", error_message=str(exc)
            )
            await db.commit()
        raise task.retry(exc=exc)

    async with session_factory() as db:
        # Xóa transcript cũ nếu có (retry case)
        old = await get_transcript(db, meeting_uuid)
        if old:
            await db.delete(old)
            await db.flush()

        transcript = await create_transcript(
            db,
            meeting_id=meeting_uuid,
            raw_text=raw_text,
            diarized_text=diarized_text,
            language=language,
        )
        await update_meeting_status(db, meeting_uuid, status="transcribed")
        await db.commit()

    logger.info(f"[transcribe_task] Xong: transcript_id={transcript.id}")
    return {"transcript_id": str(transcript.id), "char_count": transcript.char_count}
