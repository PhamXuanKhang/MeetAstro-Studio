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


def main():
    if not _HAS_RECORDER:
        send({"status": "error", "error": f"Không thể import AudioRecorder: {_IMPORT_ERROR}"})
        sys.exit(1)

    recorder: AudioRecorder | None = None

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

                recorder = AudioRecorder(
                    output_dir=output_dir,
                    sample_rate=sample_rate,
                    channels=channels,
                    mic_enabled=mic_enabled,
                    mic_gain=mic_gain,
                    sys_gain=sys_gain,
                )
                output_path = recorder.start()
                send({"status": "recording", "output_path": output_path})
            except Exception as e:
                send({"status": "error", "error": str(e)})

        elif action == "stop":
            if recorder is None or not recorder.is_recording:
                send({"status": "error", "error": "Không có recording nào đang chạy."})
                continue

            try:
                recorder.stop()
                output_path = recorder.output_path or ""
                send({"status": "stopped", "output_path": output_path})
            except Exception as e:
                send({"status": "error", "error": str(e)})
            finally:
                recorder = None

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
            send({"status": "bye"})
            break

        else:
            send({"status": "error", "error": f"Unknown action: {action}"})


if __name__ == "__main__":
    main()
