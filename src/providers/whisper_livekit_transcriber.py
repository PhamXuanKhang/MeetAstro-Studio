"""
WhisperLiveKit local transcription provider.

Connects to a WhisperLiveKit server via WebSocket and streams PCM audio
for low-latency transcription with speaker diarization.

Server must be running with:
    wlk serve --host 0.0.0.0 --port 8000 --model large-v3-turbo \
              --diarization --pcm-input --min-chunk-size 0.256

The server expects raw PCM s16le (16kHz mono) and returns JSON messages
with diarized segments in the "lines" field.
"""
import asyncio
import json
import os
import subprocess
import time
from typing import Callable, Optional

import websockets

from src.config import get_logger, get_settings
from src.providers.base_transcriber import BaseTranscriber

logger = get_logger(__name__)

_MAX_RETRIES = 2
_RETRY_BASE_DELAY = 3.0
_CHUNK_BYTES = 8192  # 0.256s @ 16kHz mono s16le


class DiarizedSegment(dict):
    """A conversation segment from diarization results."""

    speaker: str
    start: float
    end: float
    text: str


def _parse_server_time(t: str) -> float:
    """Parse server time string 'HH:MM:SS.xxx' to float seconds."""
    parts = t.split(":")
    return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])


def _run_ffmpeg_to_pcm(audio_path: str) -> subprocess.Popen:
    """Start ffmpeg subprocess to convert audio to PCM16 16kHz mono.

    Args:
        audio_path: Path to any supported audio/video file.

    Returns:
        Live Popen process whose stdout is raw PCM s16le bytes.
    """
    cmd = [
        "ffmpeg",
        "-i", audio_path,
        "-f", "s16le",
        "-ac", "1",
        "-ar", "16000",
        "-",
    ]
    return subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )


async def _stream_audio_to_ws(
    ws,
    pcm_process: subprocess.Popen,
) -> None:
    """Stream PCM chunks from ffmpeg subprocess into the WebSocket.

    Sends an empty bytes message at the end to signal EOF to the server.
    """
    while True:
        assert pcm_process.stdout is not None, "ffmpeg stdout closed unexpectedly"
        chunk = pcm_process.stdout.read(_CHUNK_BYTES)
        if not chunk:
            break
        await ws.send(chunk)

    # Signal end-of-stream
    await ws.send(b"")
    pcm_process.wait()


async def _collect_diarization_results(ws) -> list[dict]:
    """Read WebSocket messages until server signals 'ready_to_stop'.

    Accumulates the most recent complete set of lines from the server.
    """
    lines: list[dict] = []

    while True:
        msg = await ws.recv()
        data = json.loads(msg)

        if data.get("type") == "ready_to_stop":
            break

        if "lines" in data:
            lines = data["lines"]

    return lines


async def _transcribe_ws_async(
    audio_path: str,
    ws_url: str,
) -> list[dict]:
    """Establish WebSocket, stream audio, and return parsed diarization lines."""
    async with websockets.connect(ws_url) as ws:
        # Start ffmpeg in parallel with WebSocket
        pcm_proc = _run_ffmpeg_to_pcm(audio_path)

        # Stream audio to server while collecting results concurrently
        recv_task = asyncio.create_task(_collect_diarization_results(ws))
        send_task = asyncio.create_task(_stream_audio_to_ws(ws, pcm_proc))

        await asyncio.gather(send_task, recv_task)
        return recv_task.result()


async def stream_to_callback(
    audio_path: str,
    ws_url: str,
    on_partial: Callable[[list[dict]], None],
) -> list[dict]:
    """
    Stream audio via WebSocket, calling on_partial(lines) each time server sends results.

    This enables real-time partial results (e.g., SSE to frontend, terminal output)
    without waiting for the entire audio to be processed.

    This is an async function — use with `await` or `asyncio.run()`.

    Args:
        audio_path: Path to the audio/video file.
        ws_url: WebSocket URL of the WhisperLiveKit server.
        on_partial: Callback invoked each time the server sends updated lines.
                    Receives the full accumulated list of lines so far.

    Returns:
        The final list of lines when server signals 'ready_to_stop'.

    Raises:
        FileNotFoundError: If the audio file does not exist.
        RuntimeError: If the WebSocket connection or streaming fails.
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    lines: list[dict] = []

    async def sender(pcm_proc: subprocess.Popen) -> None:
        while True:
            assert pcm_proc.stdout is not None, "ffmpeg stdout closed unexpectedly"
            chunk = pcm_proc.stdout.read(_CHUNK_BYTES)
            if not chunk:
                break
            await ws.send(chunk)
        await ws.send(b"")  # EOF signal
        pcm_proc.wait()

    async def receiver() -> None:
        nonlocal lines
        while True:
            msg = await ws.recv()
            data = json.loads(msg)
            if data.get("type") == "ready_to_stop":
                break
            if "lines" in data:
                lines = data["lines"]
                on_partial(lines)  # yield partial results immediately

    pcm_proc = _run_ffmpeg_to_pcm(audio_path)
    async with websockets.connect(ws_url) as ws:
        await asyncio.gather(sender(pcm_proc), receiver())
        # Small delay to let server send any final messages before closing
        await asyncio.sleep(0.5)

    return lines


def _convert_to_seconds(audio_path: str) -> float:
    """Return audio duration in seconds by probing with ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        audio_path,
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def _run_async(coro):
    """Run coroutine safely inside Celery worker or sync context.

    If an event loop is already running (e.g., inside asyncio.run()),
    we cannot nest another asyncio.run(). Instead, create a new thread
    with its own event loop to run the coroutine.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop - safe to create one
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    else:
        # Running loop exists - spawn a thread with its own loop
        import threading

        result: list = []

        def _thread_target():
            thread_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(thread_loop)
            try:
                result.append(thread_loop.run_until_complete(coro))
            finally:
                thread_loop.close()

        thread = threading.Thread(target=_thread_target)
        thread.start()
        thread.join()
        return result[0]


class WhisperLiveKitDiarizeTranscriber(BaseTranscriber):
    """Transcriber using a local/self-hosted WhisperLiveKit WebSocket server.

    Requires a running WhisperLiveKit server with:
      - Diarization enabled (--diarization)
      - PCM input mode (--pcm-input)

    Falls back to streaming via temporary WAV file if the source is not
    already in the right format, keeping the public API identical to the
    OpenAI counterpart.
    """

    def __init__(self, url: Optional[str] = None) -> None:
        """
        Initialize the transcriber.

        Args:
            url: WebSocket URL of the WhisperLiveKit server.
                 If None, reads from WHISPER_LIVEKIT_URL setting.
        """
        settings = get_settings()
        self._url = url or settings.whisper_livekit_url
        if not self._url:
            raise ValueError(
                "WhisperLiveKit URL is not configured. "
                "Set WHISPER_LIVEKIT_URL in your environment or .env file."
            )

    def transcribe(self, audio_path: str, language: Optional[str] = None) -> str:
        """
        Transcribe audio with diarization, returns speaker-labeled string.

        Output format:
            [Speaker 0]: Today we're meeting about...
            [Speaker 1]: Yes, I agree...

        Args:
            audio_path: Path to the audio/video file.
            language: Language code (unused — model uses server-side config).

        Returns:
            Transcribed text with speaker labels.
        """
        segments = self.transcribe_to_segments(audio_path, language=language)
        return self._segments_to_string(segments)

    def transcribe_to_segments(
        self,
        audio_path: str,
        language: Optional[str] = None,
    ) -> list[DiarizedSegment]:
        """
        Transcribe audio and return structured diarization segments.

        Each segment: {speaker, start, end, text}.
        Speaker values come from the server as integers (0, 1, …) and are
        prefixed with "Speaker " to match the output format convention.

        Args:
            audio_path: Path to the audio/video file.
            language: Language code (unused).

        Returns:
            List of diarized segments.

        Raises:
            FileNotFoundError: If the audio file does not exist.
            RuntimeError: If all retry attempts fail.
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        last_error: Exception = RuntimeError("Unknown error")

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                logger.info(
                    "WhisperLiveKit WS transcription (attempt %d/%d): %s",
                    attempt,
                    _MAX_RETRIES,
                    audio_path,
                )
                start_time = time.monotonic()

                lines = _run_async(stream_to_callback(audio_path, self._url, lambda _: None))

                elapsed = time.monotonic() - start_time
                duration = _convert_to_seconds(audio_path)
                rtf = elapsed / duration if duration > 0 else 0.0

                logger.info(
                    "WhisperLiveKit diarization done: %d segments, %.1fs elapsed (RTF=%.2f).",
                    len(lines),
                    elapsed,
                    rtf,
                )

                return self._parse_lines(lines)

            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.warning(
                    "WhisperLiveKit attempt %d failed: %s. Retrying in %.1fs...",
                    attempt,
                    exc,
                    _RETRY_BASE_DELAY,
                )
                if attempt < _MAX_RETRIES:
                    time.sleep(_RETRY_BASE_DELAY * (2 ** (attempt - 1)))

        raise RuntimeError(
            f"WhisperLiveKitDiarizeTranscriber failed after {_MAX_RETRIES} "
            f"attempt(s): {last_error}"
        ) from last_error

    def _parse_lines(self, lines: list[dict]) -> list[DiarizedSegment]:
        """Parse server 'lines' dicts into DiarizedSegment list.

        Server returns: {speaker: int, start: "HH:MM:SS.xxx", end: "HH:MM:SS.xxx", text: str}
        Speaker value -2 means "no speaker detected" and is skipped.
        """
        result: list[DiarizedSegment] = []

        for line in lines:
            speaker_raw = line.get("speaker")
            if speaker_raw == -2:
                continue  # skip no-speaker placeholder

            start = _parse_server_time(line["start"])
            end = _parse_server_time(line["end"])
            text = line.get("text", "").strip()

            if not text:
                continue

            if isinstance(speaker_raw, int):
                speaker = f"Speaker {speaker_raw}"
            else:
                speaker = str(speaker_raw)

            result.append(
                DiarizedSegment(speaker=speaker, start=start, end=end, text=text)
            )

        return result

    @staticmethod
    def _segments_to_string(segments: list[DiarizedSegment]) -> str:
        """Convert segment list to speaker-labeled multi-line string.

        Adjacent segments from the same speaker are merged for readability.
        Output format matches OpenAIDiarizeTranscriber exactly:
            [Speaker 0]: Text here...
            [Speaker 1]: More text...
        """
        if not segments:
            return ""

        lines: list[str] = []
        current_speaker = segments[0]["speaker"]
        current_parts: list[str] = [segments[0]["text"]]

        for seg in segments[1:]:
            if seg["speaker"] == current_speaker:
                current_parts.append(seg["text"])
            else:
                lines.append(f"[{current_speaker}]: {' '.join(current_parts)}")
                current_speaker = seg["speaker"]
                current_parts = [seg["text"]]

        lines.append(f"[{current_speaker}]: {' '.join(current_parts)}")
        return "\n".join(lines)
