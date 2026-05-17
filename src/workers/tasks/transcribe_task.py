"""
Celery task: transcribe audio file and save transcript segments to database.

Input:  meeting_id (str), audio_path (str), diarize (bool), language (str | None)
Output: {"segment_count": int, "char_count": int}
"""
import re
from typing import Optional

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
    language: Optional[str] = None,
    cleanup_audio: bool = True,
) -> dict:
    """
    Transcribe audio and save segments to transcript_segments table.

    Args:
        meeting_id: UUID of the meeting.
        audio_path: Path to the audio file.
        diarize: Whether to perform speaker diarization.
        language: Language code for transcription. If None, provider auto-detects.
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
        segments: list[dict]
        if diarize:
            from src.services.transcription_service import (
                transcribe_diarized,
                transcribe_diarized_segments,
            )
            segments = transcribe_diarized_segments(audio_path, language=language)
            if segments:
                raw_text = _segments_to_text(segments)
            else:
                raw_text = transcribe_diarized(audio_path, language=language)
                segments = _parse_text_to_segments(raw_text)
        else:
            from src.services.transcription_service import transcribe
            raw_text = transcribe(audio_path, language=language)
            segments = _parse_text_to_segments(raw_text)
    except Exception as exc:
        update_meeting_status(meeting_id, status="failed", error_message=str(exc))
        raise self.retry(exc=exc)

    # Delete old segments if exists
    delete_transcript_segments_for_meeting(meeting_id)

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


_SPEAKER_LABEL_RE = re.compile(
    r"\[(?P<speaker>Speaker\s+\d+|[A-Z])\]\s*:?\s*"
)


def _segments_to_text(segments: list[dict]) -> str:
    lines: list[str] = []
    for seg in segments:
        text = str(seg.get("text") or "").strip()
        if not text:
            continue
        speaker = seg.get("speaker")
        prefix = f"[{speaker}]: " if speaker else ""
        lines.append(f"{prefix}{text}")
    return "\n".join(lines)


def _estimate_duration(text: str) -> float:
    word_count = len(text.split())
    return max(1.0, word_count * 0.45)


def _append_segment(
    segments: list[dict],
    speaker: str | None,
    text: str,
    cursor: float,
) -> float:
    content = text.strip()
    if not content:
        return cursor

    duration = _estimate_duration(content)
    segments.append({
        "speaker": speaker,
        "start": cursor,
        "end": cursor + duration,
        "text": content,
    })
    return cursor + duration


def _parse_text_to_segments(text: str) -> list[dict]:
    """
    Parse raw text into segments dict.

    Handles:
    1. Diarized labels: [Speaker N]: text, [A]: text, [B] text
    2. Inline diarized labels in one long line
    3. Plain continuous text
    """
    segments: list[dict] = []
    current_speaker: str | None = None
    cursor = 0.0

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        matches = list(_SPEAKER_LABEL_RE.finditer(line))
        if not matches:
            cursor = _append_segment(segments, current_speaker, line, cursor)
            continue

        leading = line[:matches[0].start()].strip()
        if leading:
            cursor = _append_segment(segments, current_speaker, leading, cursor)

        for idx, match in enumerate(matches):
            current_speaker = match.group("speaker").strip()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(line)
            content = line[match.end():end].strip()
            cursor = _append_segment(segments, current_speaker, content, cursor)

    return segments
