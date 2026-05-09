"""
Router: /api/v1/meetings/{id}/transcribe - manage transcripts.

POST /meetings/{id}/transcribe           Start transcription job (Celery, non-blocking)
GET  /meetings/{id}/transcribe/stream   Stream partial results via SSE (real-time)
GET  /meetings/{id}/transcript          Get saved transcript text
PATCH /meetings/{id}/transcript         Edit transcript
"""
import asyncio
import json
import uuid
from typing import Annotated, Any, Union

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db
from src.api.schemas.meeting_schemas import TranscriptPatch, TranscriptResponse
from src.api.schemas.task_schemas import JobStatusResponse
from src.config import get_settings
from src.db.crud.meeting_crud import get_meeting, get_transcript, update_meeting_status

router = APIRouter(prefix="/meetings", tags=["transcriptions"])


@router.post("/{meeting_id}/transcribe", response_model=JobStatusResponse)
async def start_transcription(
    meeting_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    diarize: bool = False,
    language: str = "en",
) -> JobStatusResponse:
    """Start transcription job for meeting with existing audio_path."""
    meeting = await get_meeting(db, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found.")
    if not meeting.audio_path:
        raise HTTPException(
            status_code=400, detail="Meeting has no audio. Upload audio first."
        )

    from src.workers.tasks.transcribe_task import transcribe_audio
    task = transcribe_audio.delay(
        str(meeting_id), meeting.audio_path, diarize=diarize, language=language
    )
    await update_meeting_status(
        db, meeting_id, status="transcribing", celery_task_id=task.id
    )
    return JobStatusResponse(job_id=task.id, state="PENDING")


@router.get("/{meeting_id}/transcribe/stream")
async def stream_transcribe(
    meeting_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    diarize: bool = False,
    language: str = "en",
) -> StreamingResponse:
    """
    Stream partial transcription results via Server-Sent Events (SSE).

    Streams diarized partial results as the WhisperLiveKit server processes audio,
    so the frontend can display transcripts in real-time as they are generated.

    SSE events:
        event: partial
        data: {"lines": [...], "segments": [...], "done": false}

        event: done
        data: {"done": true}

        event: error
        data: {"error": "..."}

    Frontend usage (JavaScript/Fetch):
        const es = new EventSource(`/api/v1/meetings/${id}/transcribe/stream`);
        es.addEventListener('partial', (e) => {
            const data = JSON.parse(e.data);
            appendSegments(data.segments);
        });
        es.addEventListener('done', () => es.close());

    Client can abort the stream at any time (e.g., user closes the page).
    """
    meeting = await get_meeting(db, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found.")
    if not meeting.audio_path:
        raise HTTPException(
            status_code=400, detail="Meeting has no audio. Upload audio first."
        )

    settings = get_settings()
    url = settings.whisper_livekit_url
    if not url:
        raise HTTPException(
            status_code=503,
            detail="WHISPER_LIVEKIT_URL not configured. "
                   "Enable WhisperLiveKit or use POST /transcribe for batch processing.",
        )

    async def event_generator() -> Any:
        from src.providers.whisper_livekit_transcriber import (
            _parse_server_time,
            stream_to_callback,
        )

        # Queue bridges the sync callback → async generator
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
            # Run async stream_to_callback in a thread pool so it doesn't block the event loop
            stream_future = asyncio.get_running_loop().run_in_executor(
                None,
                asyncio.run,
                stream_to_callback(
                    meeting.audio_path, url, sync_callback
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
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TranscriptResponse:
    """Get saved transcript for meeting."""
    transcript = await get_transcript(db, meeting_id)
    if not transcript:
        raise HTTPException(
            status_code=404, detail="Transcript not found. Run transcription first."
        )
    return TranscriptResponse.model_validate(transcript)


@router.patch("/{meeting_id}/transcript", response_model=TranscriptResponse)
async def patch_transcript(
    meeting_id: uuid.UUID,
    payload: TranscriptPatch,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TranscriptResponse:
    """Allow user to edit transcript before analysis."""
    transcript = await get_transcript(db, meeting_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found.")
    transcript.raw_text = payload.raw_text
    transcript.char_count = len(payload.raw_text)
    await db.flush()
    await db.refresh(transcript)
    return TranscriptResponse.model_validate(transcript)
