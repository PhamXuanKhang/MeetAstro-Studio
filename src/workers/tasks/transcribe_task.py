"""
Celery task: transcribe audio file and save transcript to database.

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
    cleanup_audio: bool = True,
) -> dict:
    """
    Transcribe audio and save to transcripts table.

    Args:
        meeting_id: UUID of the meeting.
        audio_path: Path to the audio file.
        diarize: Whether to perform speaker diarization.
        language: Language code for transcription.
        cleanup_audio: Whether to delete audio file after successful transcription.

    Returns:
        Dict with transcript_id and char_count.
    """
    return asyncio.run(
        _transcribe_async(self, meeting_id, audio_path, diarize, language, cleanup_audio)
    )


async def _transcribe_async(
    task,
    meeting_id: str,
    audio_path: str,
    diarize: bool,
    language: str,
    cleanup_audio: bool,
) -> dict:
    from src.db.crud.meeting_crud import (
        create_transcript,
        get_transcript,
        update_meeting_status,
    )
    from src.db.session import get_session_factory
    from src.services.cleanup_service import delete_audio_file
    from src.services.transcription_service import transcribe, transcribe_diarized

    session_factory = get_session_factory()

    meeting_uuid = uuid.UUID(meeting_id)
    async with session_factory() as db:
        try:
            await update_meeting_status(db, meeting_uuid, status="transcribing")
            await db.commit()
        except Exception as exc:
            logger.error("[transcribe_task] Failed to update status: %s", exc)
            raise

    try:
        logger.info("[transcribe_task] Starting transcription: %s diarize=%s", audio_path, diarize)
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

    if cleanup_audio:
        delete_audio_file(audio_path)
        logger.info("[transcribe_task] Cleaned up audio file: %s", audio_path)

    logger.info("[transcribe_task] Complete: transcript_id=%s", transcript.id)
    return {"transcript_id": str(transcript.id), "char_count": transcript.char_count}
