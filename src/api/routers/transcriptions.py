"""
Router: /api/v1/meetings/{id}/transcribe - manage transcripts.

POST /meetings/{id}/transcribe           Start transcription job (Celery, non-blocking)
GET  /meetings/{id}/transcribe/stream   Stream partial results via SSE (real-time)
GET  /meetings/{id}/transcript          Get saved transcript text
PATCH /meetings/{id}/transcript          Edit transcript
"""
import asyncio
import json
import uuid
from typing import Annotated, Any, Union

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from src.api.deps import get_supabase
from src.api.schemas.meeting_schemas import (
    TranscriptPatch,
    TranscriptResponse,
    TranscriptSegmentResponse,
)
from src.api.schemas.task_schemas import JobStatusResponse
from src.config import get_settings
from src.db.crud.meeting_crud import (
    build_transcript_text,
    create_transcript_segments,
    get_meeting,
    get_transcript_segments,
    update_meeting_status,
)
from supabase import Client

router = APIRouter(prefix="/meetings", tags=["transcriptions"])


@router.post("/{meeting_id}/transcribe", response_model=JobStatusResponse)
async def start_transcription(
    meeting_id: uuid.UUID,
    supabase: Annotated[Client, Depends(get_supabase)],
    diarize: bool = False,
    language: str = "",
) -> JobStatusResponse:
    """Start transcription job for meeting with existing audio_storage_path."""
    meeting = get_meeting(str(meeting_id))
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found.")
    if not meeting.get("audio_storage_path"):
        raise HTTPException(
            status_code=400, detail="Meeting has no audio. Upload audio first."
        )

    from src.workers.tasks.transcribe_task import transcribe_audio

    language_code = language.strip() or None
    task = transcribe_audio.delay(
        str(meeting_id),
        meeting["audio_storage_path"],
        diarize=diarize,
        language=language_code,
    )
    update_meeting_status(str(meeting_id), status="transcribing")
    return JobStatusResponse(job_id=task.id, state="PENDING")


@router.get("/{meeting_id}/transcribe/stream")
async def stream_transcribe(
    meeting_id: uuid.UUID,
    supabase: Annotated[Client, Depends(get_supabase)],
    diarize: bool = False,
    language: str = "",
) -> StreamingResponse:
    """
    Stream partial transcription results via Server-Sent Events (SSE).

    Streams diarized partial results as the WhisperLiveKit server processes audio,
    so the frontend can display transcripts in real-time as they are generated.
    """
    meeting = get_meeting(str(meeting_id))
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found.")
    if not meeting.get("audio_storage_path"):
        raise HTTPException(
            status_code=400, detail="Meeting has no audio. Upload audio first."
        )

    settings = get_settings()
    url = settings.whisper_livekit_url
    if not url:
        raise HTTPException(
            status_code=503,
            detail="WHISPER_LIVEKIT_URL not configured.",
        )

    async def event_generator() -> Any:
        from src.providers.whisper_livekit_transcriber import (
            _parse_server_time,
            stream_to_callback,
        )

        partial_queue: asyncio.Queue[Union[list[dict], Exception]] = asyncio.Queue()

        def sync_callback(lines: list[dict]) -> None:
            asyncio.get_running_loop().call_soon_threadsafe(
                partial_queue.put_nowait, lines
            )

        def build_segments(lines: list[dict]) -> list[dict]:
            result = []
            for line in lines:
                speaker_raw = line.get("speaker")
                if speaker_raw == -2:
                    continue
                text = line.get("text", "").strip()
                if not text:
                    continue
                result.append({
                    "speaker": speaker_raw,
                    "start": _parse_server_time(line["start"]),
                    "end": _parse_server_time(line["end"]),
                    "text": text,
                })
            return result

        try:
            stream_future = asyncio.get_running_loop().run_in_executor(
                None,
                asyncio.run,
                stream_to_callback(
                    meeting["audio_storage_path"], url, sync_callback
                ),
            )

            while True:
                try:
                    item = await asyncio.wait_for(partial_queue.get(), timeout=30.0)
                    if isinstance(item, Exception):
                        raise item
                    segments = build_segments(item)
                    payload = json.dumps({
                        "lines": item,
                        "segments": segments,
                        "done": False,
                    })
                    yield f"event: partial\ndata: {payload}\n\n"

                except asyncio.TimeoutError:
                    yield b": heartbeat\n\n"

                if stream_future.done():
                    try:
                        stream_future.result()
                    except Exception as exc:
                        error_payload = json.dumps({"error": str(exc)})
                        yield f"event: error\ndata: {error_payload}\n\n"
                    break

        except Exception as exc:
            error_payload = json.dumps({"error": str(exc)})
            yield f"event: error\ndata: {error_payload}\n\n"

        finally:
            yield f"event: done\ndata: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{meeting_id}/transcript", response_model=TranscriptResponse)
async def get_transcript_endpoint(
    meeting_id: uuid.UUID,
    supabase: Annotated[Client, Depends(get_supabase)],
) -> TranscriptResponse:
    """Get saved transcript for meeting (reassembled from segments)."""
    segments = get_transcript_segments(str(meeting_id))
    if not segments:
        raise HTTPException(
            status_code=404, detail="Transcript not found. Run transcription first."
        )
    text = build_transcript_text(segments)
    return TranscriptResponse(
        meeting_id=meeting_id,
        text=text,
        segments=[TranscriptSegmentResponse.model_validate(s) for s in segments],
        char_count=len(text),
    )


@router.patch("/{meeting_id}/transcript", response_model=TranscriptResponse)
async def patch_transcript(
    meeting_id: uuid.UUID,
    payload: TranscriptPatch,
    supabase: Annotated[Client, Depends(get_supabase)],
) -> TranscriptResponse:
    """Allow user to edit transcript segments before analysis."""
    meeting = get_meeting(str(meeting_id))
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found.")

    create_transcript_segments(str(meeting_id), payload.segments)
    segments = get_transcript_segments(str(meeting_id))
    text = build_transcript_text(segments)
    return TranscriptResponse(
        meeting_id=meeting_id,
        text=text,
        segments=[TranscriptSegmentResponse.model_validate(s) for s in segments],
        char_count=len(text),
    )
