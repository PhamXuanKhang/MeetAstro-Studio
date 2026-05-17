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
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import websockets

from src.config import get_logger, get_settings

logger = get_logger(__name__)


def _pcm_stats(chunk: bytes) -> tuple[int, int]:
    if len(chunk) < 2:
        return 0, 0
    samples = memoryview(chunk).cast("h")
    peak = 0
    total_sq = 0
    for sample in samples:
        value = abs(int(sample))
        peak = max(peak, value)
        total_sq += value * value
    return int((total_sq / len(samples)) ** 0.5), peak


def _with_language_query(url: str, language: Optional[str]) -> str:
    cleaned = (language or "").strip()
    if not cleaned or cleaned == "auto":
        return url
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["language"] = cleaned
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


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
        self._partial_subscribers: set[asyncio.Queue[dict]] = set()
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._partial_lines: list[dict] = []
        self._buffer_transcription = ""
        self._connected = False
        self._send_queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=200)
        self._running = False
        self._recv_task: Optional[asyncio.Task[None]] = None
        self._send_task: Optional[asyncio.Task[None]] = None
        self._ws_close_code: Optional[int] = None
        self._queued_chunks = 0
        self._sent_chunks = 0
        self._sent_bytes = 0
        self._recv_messages = 0
        self._ready_to_stop = asyncio.Event()

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

        await self._send_queue.put(chunk)
        self._queued_chunks += 1
        if self._queued_chunks == 1 or self._queued_chunks % 100 == 0:
            logger.debug(
                "[%s] Queued audio chunk #%d (%d bytes, queue=%d).",
                self.meeting_id,
                self._queued_chunks,
                len(chunk),
                self._send_queue.qsize(),
            )

    def subscribe_partials(self) -> asyncio.Queue[dict]:
        queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=1)
        self._partial_subscribers.add(queue)
        return queue

    def unsubscribe_partials(self, queue: asyncio.Queue[dict]) -> None:
        self._partial_subscribers.discard(queue)

    def _publish_partial(self, payload: dict) -> None:
        for queue in list(self._partial_subscribers):
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                logger.debug("[%s] Dropped stale partial for slow subscriber.", self.meeting_id)

    async def send_eof(self) -> None:
        """Signal end-of-stream to WhisperLiveKit by sending an empty bytes message."""
        if not self._connected:
            return
        logger.info("[%s] Sending EOF signal to WhisperLiveKit.", self.meeting_id)
        await self._send_queue.put(b"")

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
                if self._ws is None:
                    break
                await self._ws.send(chunk)
                self._sent_chunks += 1
                self._sent_bytes += len(chunk)
                if chunk == b"":
                    logger.info(
                        "[%s] Sent EOF WS chunk #%d (total=%d, queue=%d).",
                        self.meeting_id,
                        self._sent_chunks,
                        self._sent_bytes,
                        self._send_queue.qsize(),
                    )
                elif self._sent_chunks == 1 or self._sent_chunks % 25 == 0:
                    rms, peak = _pcm_stats(chunk)
                    logger.info(
                        "[%s] Sent WS chunk #%d (%d bytes, total=%d, queue=%d, rms=%d, peak=%d).",
                        self.meeting_id,
                        self._sent_chunks,
                        len(chunk),
                        self._sent_bytes,
                        self._send_queue.qsize(),
                        rms,
                        peak,
                    )
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

            if isinstance(msg, bytes):
                logger.debug("[%s] Raw WS bytes message len=%d.", self.meeting_id, len(msg))
            else:
                logger.debug("[%s] Raw WS text message len=%d.", self.meeting_id, len(msg))

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
            self._recv_messages += 1
            if self._recv_messages == 1 or self._recv_messages % 100 == 0:
                logger.debug(
                    "[%s] Received WS message #%d type=%s lines=%d buffer_len=%d.",
                    self.meeting_id,
                    self._recv_messages,
                    msg_type,
                    len(data.get("lines", [])) if isinstance(data.get("lines"), list) else 0,
                    len(str(data.get("buffer_transcription", ""))),
                )

            if msg_type == "ready_to_stop":
                logger.info("[%s] WhisperLiveKit signaled ready_to_stop.", self.meeting_id)
                self._publish_partial(data)
                self._ready_to_stop.set()
                self._running = False
                break

            if "buffer_transcription" in data:
                self._buffer_transcription = str(data.get("buffer_transcription") or "").strip()

            if "lines" in data:
                self._partial_lines = data["lines"]
                self._publish_partial(data)
                if self._on_partial:
                    try:
                        self._on_partial(self._partial_lines)
                    except Exception as exc:
                        logger.warning("[%s] on_partial callback error: %s", self.meeting_id, exc)

    async def wait_until_ready_to_stop(self, timeout_seconds: float) -> bool:
        """Wait until WhisperLiveKit confirms all audio has been processed."""
        try:
            await asyncio.wait_for(self._ready_to_stop.wait(), timeout=timeout_seconds)
            return True
        except asyncio.TimeoutError:
            logger.warning(
                "[%s] Timed out waiting %.1fs for ready_to_stop.",
                self.meeting_id,
                timeout_seconds,
            )
            return False

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

        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception:
                pass
            finally:
                self._ws = None

        self._connected = False
        logger.info("[%s] Session closed.", self.meeting_id)

    @property
    def partial_lines(self) -> list[dict]:
        """Return accumulated partial transcript lines."""
        return self._partial_lines

    @property
    def buffer_transcription(self) -> str:
        """Return the latest uncommitted WhisperLiveKit transcription buffer."""
        return self._buffer_transcription

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
        language: Optional[str] = None,
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
        url = _with_language_query(url, language)

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
