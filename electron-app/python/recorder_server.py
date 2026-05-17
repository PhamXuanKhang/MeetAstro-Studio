#!/usr/bin/env python3
"""
Python sidecar cho Electron audio recording.

Giao tiếp với Electron main process qua stdin/stdout JSON lines.
Protocol:
  → {"action": "start", "config": {...}}
  ← {"status": "recording", "output_path": "..."}
  → {"action": "stop"}
  ← {"status": "stopped", "output_path": "..."}
  → {"action": "quit"}
  (process exits)

Import trực tiếp AudioRecorder từ src/modules/audio_recorder.py.
"""
import json
import math
import re
import sys
import os
import time
import queue
import threading
import traceback
import urllib.parse
import urllib.request

try:
    import websocket
    _HAS_WEBSOCKET_CLIENT = True
except ImportError:
    websocket = None
    _HAS_WEBSOCKET_CLIENT = False

# Thêm project root vào sys.path để import src.*
# Dev: electron-app/python/recorder_server.py → project root là ../..
# Packaged: resources/python/recorder_server.py và bundled modules nằm ở resources/python/src
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_CANDIDATE_ROOTS = [
    os.path.abspath(os.path.join(_SCRIPT_DIR, '..', '..')),
    _SCRIPT_DIR,
]
for _root in _CANDIDATE_ROOTS:
    if _root not in sys.path:
        sys.path.insert(0, _root)

try:
    from src.modules.audio_recorder import AudioRecorder
    from src.config import get_settings
    _HAS_RECORDER = True
except ImportError as e:
    _HAS_RECORDER = False
    _IMPORT_ERROR = str(e)


def send(payload: dict) -> None:
    """Gửi JSON response lên stdout (Electron đọc từ đây)."""
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def emit_audio_level(payload: dict) -> None:
    send({"status": "audio_level", **payload})


def _configure_file_logging() -> None:
    log_dir = os.environ.get("MEETASTRO_RECORDER_LOG_DIR")
    if not log_dir:
        return
    try:
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "recorder_server.log")
        log_file = open(log_path, "a", encoding="utf-8", buffering=1)
        sys.stderr = log_file
        print(f"[recorder_server] logging to {log_path}", file=sys.stderr, flush=True)
    except Exception:
        pass


class StreamClient:
    """Forward live PCM chunks to FastAPI recording WebSocket."""

    def __init__(self, api_base_url: str, meeting_id: str, language: str | None = None) -> None:
        self._base = api_base_url.rstrip("/")
        self._meeting_id = meeting_id
        self._language = language.strip() if isinstance(language, str) and language.strip() else None
        if self._language == "auto":
            self._language = None
        self._active = False
        self._queue: "queue.Queue[bytes]" = queue.Queue(maxsize=50)
        self._thread: threading.Thread | None = None
        self._recv_thread: threading.Thread | None = None
        self._pending = bytearray()
        self._pending_lock = threading.Lock()
        self._flush_bytes = 16000
        self._produced_chunks = 0
        self._produced_bytes = 0
        self._posted_chunks = 0
        self._posted_bytes = 0
        self._dropped_chunks = 0
        self._ws = None
        self._stop_result: dict | None = None
        self._recv_error: Exception | None = None
        self._stop_event = threading.Event()
        self._partial_lock = threading.Lock()
        self._pending_partial: dict | None = None
        self._pending_partial_signature = ""
        self._last_partial_signature = ""
        self._last_partial_emit_at = 0.0
        self._partial_emit_interval = 0.4

    @property
    def active(self) -> bool:
        return self._active

    def _audio_stats(self, chunk: bytes) -> tuple[int, int]:
        if len(chunk) < 2:
            return 0, 0
        sample_count = len(chunk) // 2
        samples = memoryview(chunk).cast("h")
        peak = 0
        total_sq = 0
        for sample in samples:
            value = abs(int(sample))
            peak = max(peak, value)
            total_sq += value * value
        return int(math.sqrt(total_sq / sample_count)), peak

    def _enqueue_packet(self, packet: bytes) -> None:
        self._queue.put(packet, timeout=3)

    def _ws_url(self) -> str:
        parsed = urllib.parse.urlsplit(self._base)
        scheme = "wss" if parsed.scheme == "https" else "ws"
        query = urllib.parse.urlencode({"language": self._language}) if self._language else ""
        return urllib.parse.urlunsplit((
            scheme,
            parsed.netloc,
            f"/api/v1/meetings/{self._meeting_id}/recording/ws",
            query,
            "",
        ))

    def start(self) -> None:
        if not _HAS_WEBSOCKET_CLIENT or websocket is None:
            raise RuntimeError("websocket-client is not installed; Electron live streaming requires WebSocket.")
        ws_url = self._ws_url()
        print(f"[recorder_server] ws stream connecting url={ws_url}", file=sys.stderr, flush=True)
        try:
            self._ws = websocket.create_connection(ws_url, timeout=10)
            self._ws.settimeout(None)
        except Exception as exc:
            raise RuntimeError(f"Cannot connect live streaming WebSocket {ws_url}: {exc}") from exc
        print("[recorder_server] ws stream connected", file=sys.stderr, flush=True)
        self._active = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
        self._thread.start()
        self._recv_thread.start()

    def send_chunk(self, chunk: bytes) -> None:
        if not self._active or not chunk:
            return
        self._produced_chunks += 1
        self._produced_bytes += len(chunk)
        if self._produced_chunks == 1 or self._produced_chunks % 50 == 0:
            rms, peak = self._audio_stats(chunk)
            print(
                "[recorder_server] produced chunk "
                f"#{self._produced_chunks} bytes={len(chunk)} total_bytes={self._produced_bytes} "
                f"rms={rms} peak={peak} queue={self._queue.qsize()} "
                f"pending={len(self._pending)} flush_bytes={self._flush_bytes} drops={self._dropped_chunks}",
                file=sys.stderr,
                flush=True,
            )
        with self._pending_lock:
            self._pending.extend(chunk)
            while len(self._pending) >= self._flush_bytes:
                packet = bytes(self._pending[:self._flush_bytes])
                del self._pending[:self._flush_bytes]
                try:
                    self._enqueue_packet(packet)
                except queue.Full:
                    print("[recorder_server] stream queue full; applying backpressure failed", file=sys.stderr, flush=True)
                    self._active = False
                    return

    def _run(self) -> None:
        while self._active:
            try:
                chunk = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue
            try:
                if self._ws is None:
                    raise RuntimeError("WebSocket is not connected.")
                self._ws.send_binary(chunk)
                self._posted_chunks += 1
                self._posted_bytes += len(chunk)
                if self._posted_chunks == 1 or self._posted_chunks % 25 == 0:
                    rms, peak = self._audio_stats(chunk)
                    print(
                        "[recorder_server] posted chunk "
                        f"#{self._posted_chunks} bytes={len(chunk)} total_bytes={self._posted_bytes} "
                        f"rms={rms} peak={peak} queue={self._queue.qsize()} drops={self._dropped_chunks}",
                        file=sys.stderr,
                        flush=True,
                    )
            except Exception as exc:
                print(f"[recorder_server] ws send failed: {exc}", file=sys.stderr, flush=True)
                self._recv_error = exc
                self._active = False
                self._stop_event.set()

    def _visible_partial_signature(self, payload: dict) -> str:
        parts = []
        for segment in payload.get("segments") or []:
            text = str(segment.get("text", "")).strip() if isinstance(segment, dict) else ""
            if text:
                parts.append(text)
        if not parts:
            for line in payload.get("lines") or []:
                text = str(line.get("text", "")).strip() if isinstance(line, dict) else ""
                if text:
                    parts.append(text)
        buffer_text = str(payload.get("buffer_transcription") or "").strip()
        if buffer_text:
            parts.append(buffer_text)
        return re.sub(r"\s+", " ", " ".join(parts)).strip()

    def _queue_partial(self, payload: dict) -> None:
        signature = self._visible_partial_signature(payload)
        if not signature or signature == self._last_partial_signature:
            return
        with self._partial_lock:
            self._pending_partial = payload
            self._pending_partial_signature = signature
        self._flush_partial_if_due(force=False)

    def _flush_partial_if_due(self, force: bool) -> None:
        now = time.monotonic()
        if not force and now - self._last_partial_emit_at < self._partial_emit_interval:
            return
        with self._partial_lock:
            payload = self._pending_partial
            signature = self._pending_partial_signature
            self._pending_partial = None
            self._pending_partial_signature = ""
        if payload is None or not signature or signature == self._last_partial_signature:
            return
        send({"status": "stream_partial", "segments": payload.get("segments") or []})
        self._last_partial_signature = signature
        self._last_partial_emit_at = now

    def _recv_loop(self) -> None:
        while self._active or not self._stop_event.is_set():
            try:
                if self._ws is None:
                    return
                raw = self._ws.recv()
                payload = json.loads(raw)
                msg_type = payload.get("type")
                if msg_type == "stopped":
                    if payload.get("segments"):
                        self._queue_partial({"segments": payload.get("segments") or []})
                    self._flush_partial_if_due(force=True)
                    self._stop_result = payload
                    self._stop_event.set()
                    return
                if msg_type == "partial" and payload.get("segments"):
                    self._queue_partial(payload)
                    continue
                if msg_type == "error":
                    print(f"[recorder_server] ws event error={payload}", file=sys.stderr, flush=True)
            except json.JSONDecodeError:
                print(f"[recorder_server] ws ignored non-json message={str(raw)[:200]}", file=sys.stderr, flush=True)
            except Exception as exc:
                self._recv_error = exc
                if self._active or not self._stop_event.is_set():
                    print(f"[recorder_server] ws receive failed: {exc}", file=sys.stderr, flush=True)
                self._stop_event.set()
                return

    def stop(self, audio_path: str | None = None) -> dict:
        if not self._active:
            print("[recorder_server] stream stop after inactive client; still sending stop", file=sys.stderr, flush=True)
        with self._pending_lock:
            pending_bytes = len(self._pending)
            if self._pending:
                try:
                    self._enqueue_packet(bytes(self._pending))
                except queue.Full:
                    print("[recorder_server] stream queue full while flushing stop", file=sys.stderr, flush=True)
                self._pending.clear()
        backlog = self._queue.qsize()
        print(
            "[recorder_server] stream stop begin "
            f"backlog={backlog} pending_flushed={pending_bytes}B produced={self._produced_chunks}/{self._produced_bytes}B "
            f"posted={self._posted_chunks}/{self._posted_bytes}B drops={self._dropped_chunks} flush_bytes={self._flush_bytes}",
            file=sys.stderr,
            flush=True,
        )
        self._active = False
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        drained = 0
        try:
            while True:
                chunk = self._queue.get_nowait()
                if self._ws is None:
                    raise RuntimeError("WebSocket is not connected while draining stop backlog.")
                self._ws.send_binary(chunk)
                drained += 1
        except queue.Empty:
            pass
        print(f"[recorder_server] stream stop sending ws control drained={drained}", file=sys.stderr, flush=True)
        if self._ws is None:
            raise RuntimeError("WebSocket is not connected for stop.")
        self._ws.send(json.dumps({"type": "stop"}))
        if not self._stop_event.wait(timeout=90):
            raise RuntimeError("Timed out waiting for WebSocket stop response.")
        if self._stop_result is None:
            raise RuntimeError(f"WebSocket closed before stop response: {self._recv_error}")
        result = self._stop_result
        print(f"[recorder_server] ws stop payload={result}", file=sys.stderr, flush=True)
        self._ws.close()
        self._ws = None
        print("[recorder_server] stream stop done", file=sys.stderr, flush=True)
        return result

def main():
    _configure_file_logging()
    if not _HAS_RECORDER:
        send({"status": "error", "error": f"Không thể import AudioRecorder: {_IMPORT_ERROR}"})
        sys.exit(1)

    recorder: AudioRecorder | None = None
    stream_client: StreamClient | None = None

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            msg = json.loads(line)
        except json.JSONDecodeError as e:
            send({"status": "error", "error": f"JSON parse error: {e}"})
            continue

        action = msg.get("action")

        if action == "start":
            print("[recorder_server] action=start", file=sys.stderr, flush=True)
            if recorder is not None and recorder.is_recording:
                send({"status": "error", "error": "Đã đang ghi âm."})
                continue

            config = msg.get("config", {})
            try:
                settings = get_settings()
                # Override settings từ config nếu có
                sample_rate = config.get("sample_rate", settings.audio_sample_rate)
                channels = config.get("channels", settings.audio_channels)
                mic_enabled = config.get("mic_enabled", settings.audio_mic_enabled)
                mic_gain = config.get("mic_gain", settings.audio_mic_gain)
                sys_gain = config.get("sys_gain", settings.audio_sys_gain)
                output_dir = config.get("output_dir", settings.audio_output_dir)
                meeting_id = config.get("meeting_id")
                api_base_url = config.get("api_base_url")
                stream_enabled = bool(config.get("stream_enabled") and meeting_id and api_base_url)

                stream_client = None
                stream_error = None
                language = config.get("language")
                if stream_enabled:
                    try:
                        stream_client = StreamClient(str(api_base_url), str(meeting_id), language=language)
                        stream_client.start()
                        print("[recorder_server] stream start ok", file=sys.stderr, flush=True)
                    except Exception as exc:
                        stream_error = str(exc)
                        print(f"[recorder_server] stream start failed: {stream_error}", file=sys.stderr, flush=True)
                        stream_client = None

                recorder = AudioRecorder(
                    output_dir=output_dir,
                    sample_rate=sample_rate,
                    channels=channels,
                    mic_enabled=mic_enabled,
                    mic_gain=mic_gain,
                    sys_gain=sys_gain,
                    on_chunk=stream_client.send_chunk if stream_client is not None else None,
                    on_level=emit_audio_level,
                )
                output_path = recorder.start()
                time.sleep(2.1)
                if recorder.error:
                    if stream_client is not None:
                        try:
                            stream_client.stop(output_path)
                        except Exception:
                            pass
                    send({"status": "error", "error": recorder.error, "mic_error": recorder.mic_error})
                    print(f"[recorder_server] recorder start failed: {recorder.error}", file=sys.stderr, flush=True)
                    recorder = None
                    stream_client = None
                    continue
                send({
                    "status": "recording",
                    "output_path": output_path,
                    "streaming": stream_client is not None and stream_client.active,
                    "stream_error": stream_error,
                    "mic_active": recorder.mic_active,
                    "mic_error": recorder.mic_error,
                })
                print("[recorder_server] start response sent", file=sys.stderr, flush=True)
            except Exception as e:
                traceback.print_exc(file=sys.stderr)
                send({"status": "error", "error": str(e)})

        elif action == "stop":
            print("[recorder_server] action=stop", file=sys.stderr, flush=True)
            if recorder is None or not recorder.is_recording:
                send({"status": "error", "error": "Không có recording nào đang chạy."})
                continue

            try:
                recorder.stop()
                output_path = recorder.output_path or ""
                stream_error = None
                stream_result = {}
                if stream_client is not None:
                    try:
                        stream_result = stream_client.stop(output_path)
                    except Exception as exc:
                        stream_error = str(exc)
                        print(f"[recorder_server] stream stop failed: {stream_error}", file=sys.stderr, flush=True)
                send({
                    "status": "stopped",
                    "output_path": output_path,
                    "stream_error": stream_error,
                    "stream_result": stream_result,
                })
                print("[recorder_server] stop response sent", file=sys.stderr, flush=True)
            except Exception as e:
                send({"status": "error", "error": str(e)})
                print(f"[recorder_server] stop failed: {e}", file=sys.stderr, flush=True)
            finally:
                recorder = None
                stream_client = None

        elif action == "status":
            is_rec = recorder is not None and recorder.is_recording
            path = (recorder.output_path if recorder else None) or ""
            send({"status": "ok", "is_recording": is_rec, "output_path": path})

        elif action == "quit":
            if recorder is not None and recorder.is_recording:
                try:
                    recorder.stop()
                except Exception:
                    pass
            if stream_client is not None:
                try:
                    stream_client.stop()
                except Exception:
                    pass
            send({"status": "bye"})
            break

        else:
            send({"status": "error", "error": f"Unknown action: {action}"})


if __name__ == "__main__":
    main()

