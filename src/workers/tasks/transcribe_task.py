"""
Celery task: transcribe audio file and save transcript to database.

Input:  meeting_id (str), audio_path (str), diarize (bool), language (str)
Output: {"transcript_id": str, "char_count": int}
"""
from src.config import get_logger
from src.db.crud.meeting_crud import (
    create_transcript,
    delete_transcript_for_meeting,
    update_meeting_status,
)
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
    logger.info("[transcribe_task] Starting transcription: %s diarize=%s", audio_path, diarize)

    try:
        update_meeting_status(meeting_id, status="transcribing")
    except Exception as exc:
        logger.error("[transcribe_task] Failed to update status: %s", exc)
        raise

    try:
        if diarize:
            from src.services.transcription_service import transcribe_diarized
            raw_text = transcribe_diarized(audio_path, language=language)
            diarized_text = raw_text
        else:
            from src.services.transcription_service import transcribe
            raw_text = transcribe(audio_path, language=language)
            diarized_text = None
    except Exception as exc:
        update_meeting_status(meeting_id, status="failed", error_message=str(exc))
        raise self.retry(exc=exc)

    # Delete old transcript if exists
    delete_transcript_for_meeting(meeting_id)

    # Save new transcript
    transcript = create_transcript(
        meeting_id=meeting_id,
        raw_text=raw_text,
        diarized_text=diarized_text,
        language=language,
    )
    update_meeting_status(meeting_id, status="transcribed")

    if cleanup_audio:
        from src.services.cleanup_service import delete_audio_file
        delete_audio_file(audio_path)
        logger.info("[transcribe_task] Cleaned up audio file: %s", audio_path)

    logger.info("[transcribe_task] Complete: transcript_id=%s", transcript.get("id"))
    return {"transcript_id": str(transcript.get("id")), "char_count": transcript.get("char_count")}
