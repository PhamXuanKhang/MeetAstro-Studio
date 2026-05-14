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
import sys
import os
import queue
import threading
import urllib.request

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


class StreamClient:
    """Forward live PCM chunks to FastAPI recording endpoints."""

    def __init__(self, api_base_url: str, meeting_id: str) -> None:
        self._base = api_base_url.rstrip("/")
        self._meeting_id = meeting_id
        self._active = False
        self._queue: "queue.Queue[bytes]" = queue.Queue(maxsize=50)
        self._thread: threading.Thread | None = None
        self._pending = bytearray()
        self._pending_lock = threading.Lock()
        self._flush_bytes = 32000
        self._produced_chunks = 0
        self._produced_bytes = 0
        self._posted_chunks = 0
        self._posted_bytes = 0
        self._dropped_chunks = 0

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
        try:
            self._queue.put_nowait(packet)
        except queue.Full:
            try:
                self._queue.get_nowait()
                self._dropped_chunks += 1
                self._queue.put_nowait(packet)
                if self._dropped_chunks == 1 or self._dropped_chunks % 25 == 0:
                    print(
                        "[recorder_server] stream queue full "
                        f"drops={self._dropped_chunks} produced={self._produced_chunks} "
                        f"posted={self._posted_chunks} queue={self._queue.qsize()} packet_bytes={len(packet)}",
                        file=sys.stderr,
                        flush=True,
                    )
            except queue.Empty:
                pass

    def _post(self, path: str, body: bytes = b"") -> None:
        req = urllib.request.Request(
            f"{self._base}/api/v1/meetings/{self._meeting_id}/recording/{path}",
            data=body,
            method="POST",
        )
        if path == "chunk":
            boundary = "----meetastrochunk"
            payload = (
                f"--{boundary}\r\n"
                'Content-Disposition: form-data; name="chunk"; filename="chunk.pcm"\r\n'
                "Content-Type: application/octet-stream\r\n\r\n"
            ).encode("utf-8") + body + f"\r\n--{boundary}--\r\n".encode("utf-8")
            req = urllib.request.Request(
                f"{self._base}/api/v1/meetings/{self._meeting_id}/recording/chunk",
                data=payload,
                method="POST",
                headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            )
        with urllib.request.urlopen(req, timeout=3) as resp:
            resp.read()

    def start(self) -> None:
        self._post("start")
        self._active = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

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
                self._enqueue_packet(packet)

    def _run(self) -> None:
        while self._active:
            try:
                chunk = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue
            try:
                self._post("chunk", chunk)
                self._posted_chunks += 1
                self._posted_bytes += len(chunk)
                if self._posted_chunks == 1 or self._posted_chunks % 25 == 0:
                    print(
                        "[recorder_server] posted chunk "
                        f"#{self._posted_chunks} bytes={len(chunk)} total_bytes={self._posted_bytes} "
                        f"queue={self._queue.qsize()} drops={self._dropped_chunks}",
                        file=sys.stderr,
                        flush=True,
                    )
            except Exception as exc:
                print(f"[recorder_server] post chunk failed: {exc}", file=sys.stderr, flush=True)
                self._active = False

    def stop(self) -> None:
        if not self._active:
            return
        with self._pending_lock:
            pending_bytes = len(self._pending)
            if self._pending:
                self._enqueue_packet(bytes(self._pending))
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
            while drained < 3:
                self._post("chunk", self._queue.get_nowait())
                drained += 1
        except queue.Empty:
            pass
        finally:
            print(f"[recorder_server] stream stop posting eof drained={drained}", file=sys.stderr, flush=True)
            self._post("stop")
            print("[recorder_server] stream stop done", file=sys.stderr, flush=True)


def main():
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
                if stream_enabled:
                    try:
                        stream_client = StreamClient(str(api_base_url), str(meeting_id))
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
                )
                output_path = recorder.start()
                send({
                    "status": "recording",
                    "output_path": output_path,
                    "streaming": stream_client is not None and stream_client.active,
                    "stream_error": stream_error,
                })
                print("[recorder_server] start response sent", file=sys.stderr, flush=True)
            except Exception as e:
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
                if stream_client is not None:
                    try:
                        stream_client.stop()
                    except Exception as exc:
                        stream_error = str(exc)
                        print(f"[recorder_server] stream stop failed: {stream_error}", file=sys.stderr, flush=True)
                send({"status": "stopped", "output_path": output_path, "stream_error": stream_error})
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
