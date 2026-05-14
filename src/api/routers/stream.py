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
_chunk_debug_counts: dict[str, int] = {}
_chunk_debug_bytes: dict[str, int] = {}

router = APIRouter(tags=["streaming"])


def _parse_server_time(t: str) -> float:
    """Parse server time string 'HH:MM:SS.xxx' to float seconds."""
    parts = t.split(":")
    return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])


def _build_segments(lines: list[dict]) -> tuple[list[dict], dict]:
    """Parse raw server lines into frontend-friendly segment dicts."""
    result = []
    stats = {"empty_text": 0, "parse_error": 0, "non_dict": 0}
    for line in lines:
        if not isinstance(line, dict):
            stats["non_dict"] += 1
            continue
        speaker_raw = line.get("speaker")
        text = str(line.get("text", "")).strip()
        if not text:
            stats["empty_text"] += 1
            continue
        try:
            start = _parse_server_time(str(line.get("start", "00:00:00.000")))
            end = _parse_server_time(str(line.get("end", "00:00:00.000")))
        except Exception:
            stats["parse_error"] += 1
            start = 0.0
            end = 0.0
        if speaker_raw == -2 or speaker_raw is None:
            speaker = "Speaker ?"
        else:
            speaker = speaker_raw if isinstance(speaker_raw, str) else f"Speaker {speaker_raw}"
        result.append({"speaker": speaker, "start": start, "end": end, "text": text})
    return result, stats


class _SSEPoller:
    """Wraps a StreamSession to expose an async iterator over new partial results."""

    def __init__(self, session: StreamSession) -> None:
        self._session = session
        self._last_snapshot = ""

    async def __anext__(self) -> tuple[list[dict], bool]:
        """Return (segments, done). Blocks until new lines arrive or session closes."""
        while True:
            if not self._session.is_connected:
                return [], True
            lines = self._session.partial_lines
            buffer_text = self._session.buffer_transcription
            snapshot = json.dumps(
                {"lines": lines, "buffer_transcription": buffer_text},
                sort_keys=True,
                ensure_ascii=False,
            )
            if snapshot and snapshot != self._last_snapshot:
                self._last_snapshot = snapshot
                segments, stats = _build_segments(lines)
                if not segments and buffer_text:
                    segments = [{"speaker": "Speaker ?", "start": 0.0, "end": 0.0, "text": buffer_text}]
                logger.info(
                    "[%s] SSE partial snapshot changed: raw_lines=%d buffer_len=%d segments=%d stats=%s raw=%s.",
                    self._session.meeting_id,
                    len(lines),
                    len(buffer_text),
                    len(segments),
                    stats,
                    snapshot[:2000],
                )
                return segments, False
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

    key = str(meeting_id)
    _chunk_debug_counts[key] = _chunk_debug_counts.get(key, 0) + 1
    _chunk_debug_bytes[key] = _chunk_debug_bytes.get(key, 0) + len(data)
    chunk_count = _chunk_debug_counts[key]
    if chunk_count == 1 or chunk_count % 25 == 0:
        logger.info(
            "[%s] HTTP chunk received #%d bytes=%d total_bytes=%d.",
            meeting_id,
            chunk_count,
            len(data),
            _chunk_debug_bytes[key],
        )

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
    logger.info("[%s] SSE client connecting.", meeting_id)
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
                    logger.info("[%s] SSE client disconnected.", meeting_id)
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
