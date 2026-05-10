"""
Router: /api/v1/stream - Realtime audio streaming via WhisperLiveKit.

Endpoints are designed for the Electron Python sidecar:
  POST /stream/{meeting_id}/start   - Create session, connect to WhisperLiveKit WS
  POST /stream/{meeting_id}/chunk   - Forward raw PCM audio chunk (binary)
  POST /stream/{meeting_id}/stop    - Signal EOF, close session
  GET  /stream/{meeting_id}/events - SSE stream of partial transcript results

SSE event types:
  event: partial  → {"lines": [...], "segments": [...], "done": false}
  event: done     → {"done": true}
  event: error    → {"error": "..."}

Electron sidecar usage (Python):
  requests.post(f"{API}/stream/{mid}/start")
  while recording:
      chunk = get_audio_chunk()          # 16kHz mono s16le PCM
      requests.post(f"{API}/stream/{mid}/chunk", data=chunk)
  requests.post(f"{API}/stream/{mid}/stop")

Electron frontend usage (TypeScript):
  const es = new EventSource(`${API}/stream/${mid}/events`);
  es.addEventListener('partial', (e) => appendSegments(JSON.parse(e.data).segments));
  es.addEventListener('done', () => console.log('done'));
"""
import asyncio
import json
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db
from src.config import get_logger
from src.db.crud.meeting_crud import get_meeting, update_meeting_status
from src.services.stream_session_manager import StreamSession, get_stream_manager

logger = get_logger(__name__)

router = APIRouter(prefix="/stream", tags=["streaming"])


# ── Helpers ─────────────────────────────────────────────────────────────────────

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


# ── SSE segment poller ──────────────────────────────────────────────────────────

class _SSEPoller:
    """Wraps a StreamSession to expose an async iterator over new partial results.

    The SSE endpoint uses this to stream transcript updates to the Electron
    frontend as soon as they arrive, without busy-waiting.
    """

    def __init__(self, session: StreamSession) -> None:
        self._session = session
        self._last_len = 0
        self._done = False

    async def __anext__(self) -> tuple[list[dict], bool]:
        """Return (segments, done). Blocks until new lines arrive or session closes."""
        while True:
            if not self._session.is_connected:
                return [], True

            lines = self._session.partial_lines
            if len(lines) > self._last_len:
                self._last_len = len(lines)
                return _build_segments(lines), False

            # Wait a short interval before checking again
            await asyncio.sleep(0.25)

            if not self._session.is_connected:
                return [], True


# ── Endpoints ───────────────────────────────────────────────────────────────────

@router.post("/{meeting_id}/start")
async def start_stream(
    meeting_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """
    Initialize a realtime streaming session for a meeting.

    Creates a WebSocket connection to WhisperLiveKit and returns immediately.
    The client then sends PCM audio chunks via POST /chunk.
    """
    meeting = await get_meeting(db, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found.")

    manager = get_stream_manager()

    # If session already exists, return early (idempotent)
    existing = await manager.get_session(str(meeting_id))
    if existing is not None:
        return {"session_id": str(meeting_id), "status": "active"}

    # Create and connect new session
    def _on_partial(lines: list[dict]) -> None:
        logger.debug("[%s] Received %d lines from WhisperLiveKit.", meeting_id, len(lines))

    await manager.create_session(str(meeting_id), on_partial=_on_partial)
    await update_meeting_status(db, meeting_id, status="recording")

    logger.info("[%s] Streaming session started.", meeting_id)
    return {"session_id": str(meeting_id), "status": "active"}


@router.post("/{meeting_id}/chunk")
async def send_audio_chunk(
    meeting_id: uuid.UUID,
    chunk: UploadFile = File(...),
) -> dict:
    """
    Forward a raw PCM audio chunk to WhisperLiveKit.

    The Electron sidecar sends binary PCM data (16kHz mono s16le).
    Each chunk is typically 4096 bytes ≈ 128ms of audio at 16kHz.

    Chunking strategy on the sidecar side:
        chunk_size = sample_rate * channels * bytes_per_sample * seconds
        e.g. 16000 * 1 * 2 * 0.128 ≈ 4096 bytes
    """
    manager = get_stream_manager()
    session = await manager.get_session(str(meeting_id))

    if session is None:
        raise HTTPException(
            status_code=404,
            detail=f"No active stream session for meeting {meeting_id}. "
                   "Call POST /stream/{id}/start first.",
        )

    data = await chunk.read()
    if not data:
        return {"received": 0}

    try:
        await session.send_audio_chunk(data)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return {"received": len(data)}


@router.post("/{meeting_id}/stop")
async def stop_stream(
    meeting_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """
    Signal end-of-stream to WhisperLiveKit and close the session.

    Returns the final accumulated transcript lines for the meeting so
    the caller can persist them to the database.
    """
    manager = get_stream_manager()
    session = await manager.get_session(str(meeting_id))

    if session is not None:
        await session.send_eof()
        await asyncio.sleep(0.5)  # Let WhisperLiveKit flush final results
        final_lines = session.partial_lines
        await manager.close_session(str(meeting_id))
    else:
        final_lines = []

    await update_meeting_status(db, meeting_id, status="pending")

    logger.info("[%s] Streaming session stopped with %d final lines.", meeting_id, len(final_lines))
    return {
        "status": "stopped",
        "meeting_id": str(meeting_id),
        "lines": final_lines,
    }


@router.get("/{meeting_id}/events")
async def stream_events(
    meeting_id: uuid.UUID,
) -> StreamingResponse:
    """
    SSE stream of partial transcript results.

    The Electron frontend connects here to receive real-time transcript updates
    while the meeting is being recorded.

    This endpoint is idempotent with respect to GET — multiple clients can
    connect simultaneously (e.g. main window + preview pane).

    SSE events:
        event: partial  → {"segments": [...], "done": false}
        event: done     → {"done": true}
        event: error    → {"error": "..."}

    Frontend usage:
        const es = new EventSource(`/api/v1/stream/${meetingId}/events`);
        es.addEventListener('partial', (e) => {
            const { segments } = JSON.parse(e.data);
            renderSegments(segments);
        });
        es.addEventListener('done', () => {
            console.log('Stream ended');
            es.close();
        });
        es.addEventListener('error', (e) => {
            console.error('Stream error:', e);
        });
    """
    manager = get_stream_manager()
    session = await manager.get_session(str(meeting_id))

    if session is None:
        raise HTTPException(
            status_code=404,
            detail=f"No active stream session for meeting {meeting_id}. "
                   "Call POST /stream/{id}/start first.",
        )

    poller = _SSEPoller(session)

    async def event_generator():
        try:
            while True:
                try:
                    segments, done = await poller.__anext__()

                    if done:
                        payload = json.dumps({"done": True})
                        yield f"event: done\ndata: {payload}\n\n"
                        break

                    if segments:
                        payload = json.dumps({
                            "segments": segments,
                            "done": False,
                        })
                        yield f"event: partial\ndata: {payload}\n\n"

                except asyncio.CancelledError:
                    break
                except Exception as exc:
                    logger.error("[%s] SSE generator error: %s", meeting_id, exc)
                    error_payload = json.dumps({"error": str(exc)})
                    yield f"event: error\ndata: {error_payload}\n\n"
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
