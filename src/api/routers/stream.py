"""
Router: realtime audio streaming via WhisperLiveKit.

Canonical endpoints:
  POST /meetings/{meeting_id}/recording/start
  POST /meetings/{meeting_id}/recording/chunk
  POST /meetings/{meeting_id}/recording/stop
  GET  /meetings/{meeting_id}/recording/events

Hidden legacy aliases:
  POST /stream/{meeting_id}/start
  POST /stream/{meeting_id}/chunk
  POST /stream/{meeting_id}/stop
  GET  /stream/{meeting_id}/events
"""
import asyncio
import json
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from src.config import get_logger
from src.db.crud.meeting_crud import get_meeting, update_meeting_status
from src.services.stream_session_manager import StreamSession, get_stream_manager

logger = get_logger(__name__)

MAX_RECORDING_CHUNK_BYTES = 512 * 1024

router = APIRouter(tags=["streaming"])


def _parse_server_time(t: str) -> float:
    """Parse server time string 'HH:MM:SS.xxx' to float seconds."""
    parts = t.split(":")
    return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])


def _build_segments(lines: list[dict]) -> list[dict]:
    """Parse raw server lines into frontend-friendly segment dicts."""
    result = []
    for line in lines:
        speaker_raw = line.get("speaker")
        if speaker_raw == -2:
            continue
        text = line.get("text", "").strip()
        if not text:
            continue
        start = _parse_server_time(str(line.get("start", "00:00:00.000")))
        end = _parse_server_time(str(line.get("end", "00:00:00.000")))
        speaker = speaker_raw if isinstance(speaker_raw, str) else f"Speaker {speaker_raw}"
        result.append({"speaker": speaker, "start": start, "end": end, "text": text})
    return result


class _SSEPoller:
    """Wraps a StreamSession to expose an async iterator over new partial results."""

    def __init__(self, session: StreamSession) -> None:
        self._session = session
        self._last_len = 0

    async def __anext__(self) -> tuple[list[dict], bool]:
        """Return (segments, done). Blocks until new lines arrive or session closes."""
        while True:
            if not self._session.is_connected:
                return [], True
            lines = self._session.partial_lines
            if len(lines) > self._last_len:
                self._last_len = len(lines)
                return _build_segments(lines), False
            await asyncio.sleep(0.25)
            if not self._session.is_connected:
                return [], True


@router.post("/meetings/{meeting_id}/recording/start")
@router.post("/stream/{meeting_id}/start", include_in_schema=False)
async def start_stream(meeting_id: uuid.UUID) -> dict:
    """Initialize a realtime streaming session for a meeting."""
    meeting = get_meeting(str(meeting_id))
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found.")

    manager = get_stream_manager()
    existing = await manager.get_session(str(meeting_id))
    if existing is not None:
        return {"session_id": str(meeting_id), "status": "active"}

    def _on_partial(lines: list[dict]) -> None:
        logger.debug("[%s] Received %d lines from WhisperLiveKit.", meeting_id, len(lines))

    await manager.create_session(str(meeting_id), on_partial=_on_partial)
    update_meeting_status(str(meeting_id), status="transcribing")

    logger.info("[%s] Streaming session started.", meeting_id)
    return {"session_id": str(meeting_id), "status": "active"}


@router.post("/meetings/{meeting_id}/recording/chunk")
@router.post("/stream/{meeting_id}/chunk", include_in_schema=False)
async def send_audio_chunk(
    meeting_id: uuid.UUID,
    chunk: UploadFile = File(...),
) -> dict:
    """Forward a raw PCM audio chunk to WhisperLiveKit."""
    manager = get_stream_manager()
    session = await manager.get_session(str(meeting_id))

    if session is None:
        raise HTTPException(
            status_code=404,
            detail=f"No active stream session for meeting {meeting_id}. "
                   "Call POST /meetings/{id}/recording/start first.",
        )

    data = await chunk.read(MAX_RECORDING_CHUNK_BYTES + 1)
    if len(data) > MAX_RECORDING_CHUNK_BYTES:
        raise HTTPException(status_code=413, detail="Audio chunk too large.")
    if not data:
        return {"received": 0}

    try:
        await session.send_audio_chunk(data)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return {"received": len(data)}


@router.post("/meetings/{meeting_id}/recording/stop")
@router.post("/stream/{meeting_id}/stop", include_in_schema=False)
async def stop_stream(meeting_id: uuid.UUID) -> dict:
    """Signal end-of-stream and close the session."""
    manager = get_stream_manager()
    session = await manager.get_session(str(meeting_id))

    if session is not None:
        await session.send_eof()
        await asyncio.sleep(0.5)
        final_lines = session.partial_lines
        await manager.close_session(str(meeting_id))
    else:
        final_lines = []

    update_meeting_status(str(meeting_id), status="pending")

    logger.info("[%s] Streaming session stopped with %d final lines.", meeting_id, len(final_lines))
    return {
        "status": "stopped",
        "meeting_id": str(meeting_id),
        "lines": final_lines,
    }


@router.get("/meetings/{meeting_id}/recording/events")
@router.get("/stream/{meeting_id}/events", include_in_schema=False)
async def stream_events(meeting_id: uuid.UUID) -> StreamingResponse:
    """SSE stream of partial transcript results."""
    manager = get_stream_manager()
    session = await manager.get_session(str(meeting_id))

    if session is None:
        raise HTTPException(
            status_code=404,
            detail=f"No active stream session for meeting {meeting_id}. "
                   "Call POST /meetings/{id}/recording/start first.",
        )

    poller = _SSEPoller(session)

    async def event_generator():
        try:
            while True:
                try:
                    segments, done = await poller.__anext__()
                    if done:
                        yield f"event: done\ndata: {json.dumps({'done': True})}\n\n"
                        break
                    if segments:
                        payload = json.dumps({"segments": segments, "done": False})
                        yield f"event: partial\ndata: {payload}\n\n"
                except asyncio.CancelledError:
                    break
                except Exception as exc:
                    logger.error("[%s] SSE generator error: %s", meeting_id, exc)
                    yield f"event: error\ndata: {json.dumps({'error': str(exc)})}\n\n"
                    break
        except GeneratorExit:
            pass
        finally:
            logger.info("[%s] SSE client disconnected.", meeting_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
