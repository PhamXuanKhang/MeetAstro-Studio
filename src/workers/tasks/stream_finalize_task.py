"""Celery task for live streaming finalize fallback."""
from typing import Optional

from src.config import get_logger, get_settings
from src.db.crud.meeting_crud import (
    create_transcript_segments,
    get_transcript_segments,
    update_meeting_status,
)
from src.workers.celery_app import celery_app
from src.workers.tasks.transcribe_task import _parse_text_to_segments

logger = get_logger(__name__)


@celery_app.task(
    name="finalize_stream_recording",
    bind=True,
    max_retries=0,
    queue="default",
)
def finalize_stream_recording(
    self,
    meeting_id: str,
    *,
    audio_path: Optional[str] = None,
    language: Optional[str] = None,
) -> dict:
    """Finalize live streaming transcript and run OpenAI fallback if needed."""
    try:
        existing_segments = get_transcript_segments(meeting_id)
        if existing_segments:
            update_meeting_status(meeting_id, status="transcribed")
            return {
                "status": "transcribed",
                "source": "whisper_livekit",
                "segment_count": len(existing_segments),
            }

        update_meeting_status(meeting_id, status="processing")

        if not audio_path:
            message = "Live recording has no usable WLK transcript and no fallback audio_path."
            update_meeting_status(meeting_id, status="failed", error_message=message)
            return {"status": "failed", "source": "none", "segment_count": 0, "error": message}

        if not get_settings().openai_api_key:
            message = "OPENAI_API_KEY is not configured for live recording fallback."
            update_meeting_status(meeting_id, status="failed", error_message=message)
            return {"status": "failed", "source": "openai", "segment_count": 0, "error": message}

        from src.services.transcription_service import transcribe

        raw_text = transcribe(audio_path, language=language)
        segments = _parse_text_to_segments(raw_text)
        if not segments:
            message = "OpenAI fallback returned empty transcript."
            update_meeting_status(meeting_id, status="failed", error_message=message)
            return {"status": "failed", "source": "openai", "segment_count": 0, "error": message}

        saved = create_transcript_segments(meeting_id, segments)
        update_meeting_status(meeting_id, status="transcribed")
        logger.info(
            "[stream_finalize_task] Complete meeting=%s source=openai segments=%d.",
            meeting_id,
            len(saved),
        )
        return {"status": "transcribed", "source": "openai", "segment_count": len(saved)}
    except Exception as exc:
        update_meeting_status(meeting_id, status="failed", error_message=str(exc))
        raise
