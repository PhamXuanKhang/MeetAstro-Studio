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

    @property
    def active(self) -> bool:
        return self._active

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
        try:
            self._queue.put_nowait(chunk)
        except queue.Full:
            try:
                self._queue.get_nowait()
                self._queue.put_nowait(chunk)
            except queue.Empty:
                pass

    def _run(self) -> None:
        while self._active:
            try:
                chunk = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue
            try:
                self._post("chunk", chunk)
            except Exception:
                self._active = False

    def stop(self) -> None:
        if not self._active:
            return
        self._active = False
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        try:
            while True:
                self._post("chunk", self._queue.get_nowait())
        except queue.Empty:
            pass
        finally:
            self._post("stop")


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
                    except Exception as exc:
                        stream_error = str(exc)
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
            except Exception as e:
                send({"status": "error", "error": str(e)})

        elif action == "stop":
            if recorder is None or not recorder.is_recording:
                send({"status": "error", "error": "Không có recording nào đang chạy."})
                continue

            try:
                recorder.stop()
                if stream_client is not None:
                    stream_client.stop()
                output_path = recorder.output_path or ""
                send({"status": "stopped", "output_path": output_path})
            except Exception as e:
                send({"status": "error", "error": str(e)})
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
