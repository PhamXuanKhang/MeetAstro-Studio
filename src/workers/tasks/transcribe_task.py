"""
Celery task: transcribe audio file and save transcript segments to database.

Input:  meeting_id (str), audio_path (str), diarize (bool), language (str)
Output: {"segment_count": int, "char_count": int}
"""
from src.config import get_logger
from src.db.crud.meeting_crud import (
    create_transcript_segments,
    delete_transcript_segments_for_meeting,
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
    Transcribe audio and save segments to transcript_segments table.

    Args:
        meeting_id: UUID of the meeting.
        audio_path: Path to the audio file.
        diarize: Whether to perform speaker diarization.
        language: Language code for transcription.
        cleanup_audio: Whether to delete audio file after successful transcription.

    Returns:
        Dict with segment_count and char_count.
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
        else:
            from src.services.transcription_service import transcribe
            raw_text = transcribe(audio_path, language=language)
    except Exception as exc:
        update_meeting_status(meeting_id, status="failed", error_message=str(exc))
        raise self.retry(exc=exc)

    # Delete old segments if exists
    delete_transcript_segments_for_meeting(meeting_id)

    # Build segments from raw_text
    segments = _parse_text_to_segments(raw_text)

    # Save segments
    saved = create_transcript_segments(meeting_id, segments)
    update_meeting_status(meeting_id, status="transcribed")

    if cleanup_audio:
        from src.services.cleanup_service import delete_audio_file
        delete_audio_file(audio_path)
        logger.info("[transcribe_task] Cleaned up audio file: %s", audio_path)

    segment_count = len(saved)
    char_count = len(raw_text)
    logger.info("[transcribe_task] Complete: %d segments, %d chars", segment_count, char_count)
    return {"segment_count": segment_count, "char_count": char_count}


def _parse_text_to_segments(text: str) -> list[dict]:
    """
    Parse raw text into segments dict.

    Handles two formats:
    1. Diarized: [Speaker N]: text  (detected by "[Speaker" prefix)
    2. Plain: continuous text lines
    """
    segments: list[dict] = []
    current_speaker: str | None = None
    current_text_parts: list[str] = []
    start_time = 0.0

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        # Detect speaker label line
        speaker_prefix: str | None = None
        if line.startswith("[Speaker"):
            bracket_end = line.index("]")
            speaker_prefix = line[:bracket_end + 1]
            content = line[bracket_end + 1:].strip()
            if content.startswith(":"):
                content = content[1:].strip()
        else:
            content = line

        if not content:
            continue

        # If speaker changed or no speaker, flush current segment
        if speaker_prefix or (current_speaker is not None and current_text_parts):
            if current_text_parts:
                segments.append({
                    "speaker": current_speaker,
                    "start": start_time,
                    "end": start_time + len(" ".join(current_text_parts)) * 0.5,
                    "text": " ".join(current_text_parts),
                })
            current_text_parts = []
            start_time = 0.0

        if speaker_prefix:
            current_speaker = speaker_prefix[1:-1]  # strip [ ]
        else:
            current_speaker = None

        current_text_parts.append(content)
        start_time += 0.5  # approximate per-word time

    # Flush remaining
    if current_text_parts:
        segments.append({
            "speaker": current_speaker,
            "start": 0.0,
            "end": start_time,
            "text": " ".join(current_text_parts),
        })

    return segments
