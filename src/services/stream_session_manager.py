"""
Stream session manager - manages live audio streaming sessions to WhisperLiveKit.

Each active meeting that is recording live audio has one StreamSession.
The session maintains a WebSocket connection to the WhisperLiveKit server,
receives raw PCM audio chunks from the Electron sidecar (via REST),
forwards them to WhisperLiveKit, and accumulates partial transcript results.
"""
import asyncio
import json
from typing import Callable, Optional

import websockets

from src.config import get_logger, get_settings

logger = get_logger(__name__)


class StreamSession:
    """Manages one live streaming session for a meeting.

    Holds a persistent WebSocket connection to WhisperLiveKit.
    Audio chunks arrive via REST POST → forwarded over WS → partial
    results are accumulated in memory for the SSE endpoint to read.
    """

    def __init__(
        self,
        meeting_id: str,
        whisper_ws_url: str,
        on_partial: Optional[Callable[[list[dict]], None]] = None,
    ) -> None:
        """
        Args:
            meeting_id: UUID string of the meeting.
            whisper_ws_url: WebSocket URL of the WhisperLiveKit server.
            on_partial: Optional callback invoked each time the server sends updated lines.
        """
        self.meeting_id = meeting_id
        self._whisper_url = whisper_ws_url
        self._on_partial = on_partial
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._partial_lines: list[dict] = []
        self._connected = False
        self._send_queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=200)
        self._running = False
        self._recv_task: Optional[asyncio.Task[None]] = None
        self._send_task: Optional[asyncio.Task[None]] = None
        self._ws_close_code: Optional[int] = None

    async def connect(self) -> None:
        """Establish WebSocket connection to WhisperLiveKit and start send/receive tasks."""
        if self._connected:
            logger.warning("[%s] Session already connected.", self.meeting_id)
            return

        logger.info("[%s] Connecting to WhisperLiveKit: %s", self.meeting_id, self._whisper_url)
        self._ws = await websockets.connect(self._whisper_url)
        self._connected = True
        self._running = True

        self._recv_task = asyncio.create_task(self._recv_loop())
        self._send_task = asyncio.create_task(self._send_loop())

        logger.info("[%s] WebSocket connected and tasks started.", self.meeting_id)

    async def send_audio_chunk(self, chunk: bytes) -> None:
        """Queue a raw PCM audio chunk to be forwarded to WhisperLiveKit.

        This method is called from the FastAPI async context (the REST endpoint)
        and safely puts the chunk into an asyncio.Queue that the send task drains.
        """
        if not self._connected:
            raise RuntimeError(f"[{self.meeting_id}] Session not connected.")

        try:
            self._send_queue.put_nowait(chunk)
        except asyncio.QueueFull:
            logger.warning(
                "[%s] Send queue full (len=%d) — dropping oldest chunk.",
                self.meeting_id,
                self._send_queue.qsize(),
            )
            try:
                self._send_queue.get_nowait()
                self._send_queue.put_nowait(chunk)
            except asyncio.QueueEmpty:
                pass

    async def send_eof(self) -> None:
        """Signal end-of-stream to WhisperLiveKit by sending an empty bytes message."""
        if not self._connected:
            return
        logger.info("[%s] Sending EOF signal to WhisperLiveKit.", self.meeting_id)
        try:
            self._send_queue.put_nowait(b"")
        except asyncio.QueueFull:
            pass

    async def _send_loop(self) -> None:
        """Drain the send queue and forward chunks to WhisperLiveKit over WebSocket."""
        while self._running:
            try:
                chunk = await asyncio.wait_for(self._send_queue.get(), timeout=2.0)
            except asyncio.TimeoutError:
                if not self._running:
                    break
                continue
            except asyncio.CancelledError:
                break

            try:
                if self._ws is not None and self._ws.open:
                    await self._ws.send(chunk)
            except Exception as exc:
                logger.error("[%s] Error sending chunk: %s", self.meeting_id, exc)
                break

    async def _recv_loop(self) -> None:
        """Read messages from WhisperLiveKit, accumulate lines, invoke callback."""
        assert self._ws is not None, "_recv_loop called before connect()"
        while self._running:
            try:
                msg = await asyncio.wait_for(self._ws.recv(), timeout=5.0)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("[%s] WebSocket recv error: %s", self.meeting_id, exc)
                break

            try:
                data = json.loads(msg)
            except json.JSONDecodeError:
                logger.warning(
                    "[%s] Non-JSON message from WhisperLiveKit: %s",
                    self.meeting_id,
                    msg,
                )
                continue

            msg_type = data.get("type")

            if msg_type == "ready_to_stop":
                logger.info("[%s] WhisperLiveKit signaled ready_to_stop.", self.meeting_id)
                self._running = False
                break

            if "lines" in data:
                self._partial_lines = data["lines"]
                if self._on_partial:
                    try:
                        self._on_partial(self._partial_lines)
                    except Exception as exc:
                        logger.warning("[%s] on_partial callback error: %s", self.meeting_id, exc)

    async def close(self) -> None:
        """Gracefully close the WebSocket connection and cancel tasks."""
        logger.info("[%s] Closing session.", self.meeting_id)
        self._running = False

        for task in (self._recv_task, self._send_task):
            if task is not None and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        if self._ws is not None and self._ws.open:
            try:
                await self._ws.close()
            except Exception:
                pass

        self._connected = False
        logger.info("[%s] Session closed.", self.meeting_id)

    @property
    def partial_lines(self) -> list[dict]:
        """Return accumulated partial transcript lines."""
        return self._partial_lines

    @property
    def is_connected(self) -> bool:
        return self._connected


class StreamSessionManager:
    """Singleton that manages all active StreamSession instances per meeting_id."""

    def __init__(self) -> None:
        self._sessions: dict[str, StreamSession] = {}
        self._lock = asyncio.Lock()

    async def create_session(
        self,
        meeting_id: str,
        on_partial: Optional[Callable[[list[dict]], None]] = None,
    ) -> StreamSession:
        """Create and connect a new streaming session for a meeting.

        If a session already exists for this meeting_id, returns the existing one.
        """
        async with self._lock:
            if meeting_id in self._sessions:
                logger.info("[%s] Reusing existing session.", meeting_id)
                return self._sessions[meeting_id]

        settings = get_settings()
        url = settings.whisper_livekit_url
        if not url:
            raise RuntimeError(
                "WHISPER_LIVEKIT_URL is not configured. "
                "Cannot start a streaming session."
            )

        session = StreamSession(meeting_id, url, on_partial=on_partial)
        await session.connect()

        async with self._lock:
            self._sessions[meeting_id] = session

        logger.info("[%s] Streaming session created.", meeting_id)
        return session

    async def get_session(self, meeting_id: str) -> Optional[StreamSession]:
        """Return the session for this meeting_id, or None if not found."""
        async with self._lock:
            return self._sessions.get(meeting_id)

    async def close_session(self, meeting_id: str) -> None:
        """Close and remove the session for this meeting_id."""
        async with self._lock:
            session = self._sessions.pop(meeting_id, None)

        if session is not None:
            await session.close()
            logger.info("[%s] Session removed from manager.", meeting_id)

    async def close_all(self) -> None:
        """Close all active sessions. Called on app shutdown."""
        async with self._lock:
            meeting_ids = list(self._sessions.keys())

        for meeting_id in meeting_ids:
            await self.close_session(meeting_id)

        logger.info("All streaming sessions closed.")


_stream_manager: Optional[StreamSessionManager] = None


def get_stream_manager() -> StreamSessionManager:
    """Return the global StreamSessionManager singleton."""
    global _stream_manager
    if _stream_manager is None:
        _stream_manager = StreamSessionManager()
    return _stream_manager
