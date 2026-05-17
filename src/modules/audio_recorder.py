"""
System audio recorder module.

Captures system audio (via pysysaudio) with optional microphone mixing and
writes the result to a single WAV file. Designed to be started / stopped
programmatically from the desktop UI.
"""
import datetime as dt
import os
import queue
import threading
import time
import wave
from typing import Callable, Optional

import numpy as np

from src.config import get_logger, get_settings

logger = get_logger(__name__)


class AudioRecorder:
    """Record system audio (+ optional mic) to a WAV file in a background thread."""

    def __init__(
        self,
        sample_rate: Optional[int] = None,
        channels: Optional[int] = None,
        mic_enabled: Optional[bool] = None,
        mic_gain: Optional[float] = None,
        sys_gain: Optional[float] = None,
        output_dir: Optional[str] = None,
        on_chunk: Optional[Callable[[bytes], None]] = None,
    ) -> None:
        """
        Initialize audio recorder.

        Args:
            sample_rate: Audio sample rate. If None, loads from settings.
            channels: Number of audio channels. If None, loads from settings.
            mic_enabled: Whether to enable microphone. If None, loads from settings.
            mic_gain: Microphone gain multiplier. If None, loads from settings.
            sys_gain: System audio gain multiplier. If None, loads from settings.
            output_dir: Output directory for recordings. If None, loads from settings.
            on_chunk: Optional callback receiving each mixed PCM chunk.
        """
        settings = get_settings()
        self._sample_rate = sample_rate if sample_rate is not None else settings.audio_sample_rate
        self._channels = channels if channels is not None else settings.audio_channels
        self._mic_enabled = mic_enabled if mic_enabled is not None else settings.audio_mic_enabled
        self._mic_gain = mic_gain if mic_gain is not None else settings.audio_mic_gain
        self._sys_gain = sys_gain if sys_gain is not None else settings.audio_sys_gain
        self._output_dir = output_dir if output_dir is not None else settings.audio_output_dir
        self._on_chunk = on_chunk

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._output_path: Optional[str] = None
        self._start_time: Optional[float] = None
        self._error: Optional[str] = None
        self._total_frames: int = 0
        self._lock = threading.Lock()

    @property
    def is_recording(self) -> bool:
        """Return True if currently recording."""
        return self._thread is not None and self._thread.is_alive()

    @property
    def output_path(self) -> Optional[str]:
        """Return the current output file path."""
        return self._output_path

    @property
    def error(self) -> Optional[str]:
        """Return any error that occurred during recording."""
        return self._error

    def start(self, output_path: Optional[str] = None) -> str:
        """
        Begin recording.

        Args:
            output_path: Optional custom output path. If None, generates timestamped filename.

        Returns:
            The output WAV file path.

        Raises:
            RuntimeError: If already recording.
        """
        if self.is_recording:
            raise RuntimeError("Already recording.")

        if output_path is None:
            ts = dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            os.makedirs(self._output_dir, exist_ok=True)
            output_path = os.path.join(self._output_dir, f"recording_{ts}.wav")

        self._output_path = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(self._output_path), exist_ok=True)

        self._stop_event.clear()
        self._error = None
        self._total_frames = 0

        self._thread = threading.Thread(target=self._record_loop, daemon=True)
        self._thread.start()

        self._start_time = time.time()
        logger.info("Recording started: %s", self._output_path)
        return self._output_path

    def stop(self) -> str:
        """
        Stop recording and return the WAV path.

        Returns:
            The output WAV file path.

        Raises:
            RuntimeError: If not currently recording or if recording failed.
        """
        if not self.is_recording or self._thread is None:
            raise RuntimeError("Not recording.")

        self._stop_event.set()
        self._thread.join(timeout=5.0)
        self._thread = None
        self._start_time = None

        if self._error:
            raise RuntimeError(f"Recording failed: {self._error}")

        if self._output_path is None:
            raise RuntimeError("No output path set.")

        duration = self._total_frames / float(self._sample_rate) if self._sample_rate else 0
        logger.info(
            "Recording stopped. Frames: %d | Duration: %.2fs | File: %s",
            self._total_frames, duration, self._output_path,
        )
        return self._output_path

    def _open_wav(self, path: str, sampwidth: int) -> wave.Wave_write:
        """Open a WAV file for writing."""
        wf = wave.open(path, "wb")
        wf.setnchannels(self._channels)
        wf.setsampwidth(sampwidth)
        wf.setframerate(self._sample_rate)
        wf.setcomptype("NONE", "not compressed")
        return wf

    def _record_loop(self) -> None:  # noqa: C901
        """Capture system audio, optionally mix mic, write WAV continuously."""
        try:
            from pysysaudio import SystemAudioRecorder as SysRecorder
        except ImportError:
            msg = (
                "pysysaudio is unavailable on this platform (not installed or "
                "unsupported — Linux has no build). Use audio file upload, or run "
                "the desktop recorder on macOS/Windows."
            )
            self._error = msg
            logger.error(msg)
            return

        sampwidth = 2  # int16

        recorder = SysRecorder(
            sample_rate=self._sample_rate,
            channels=self._channels,
            format="bytes",
            dtype="int16",
        )

        mic_q: "queue.Queue[bytes]" = queue.Queue(maxsize=200)
        mic_thread: Optional[threading.Thread] = None

        wf: Optional[wave.Wave_write] = None

        try:
            if self._output_path is None:
                raise RuntimeError("No output path set.")
            wf = self._open_wav(self._output_path, sampwidth)

            if self._mic_enabled:
                mic_thread = self._start_mic_capture(mic_q)

            recorder.start_recording()

            mic_buffer = np.empty((0,), dtype=np.int16)

            for chunk in recorder.stream(timeout=0.25):
                if self._stop_event.is_set():
                    break
                if not chunk:
                    continue

                sys_np = np.frombuffer(chunk, dtype=np.int16)

                if self._mic_enabled:
                    while True:
                        try:
                            mic_bytes = mic_q.get_nowait()
                        except queue.Empty:
                            break
                        mic_buffer = np.concatenate(
                            (mic_buffer, np.frombuffer(mic_bytes, dtype=np.int16))
                        )

                    need = sys_np.size
                    if mic_buffer.size >= need:
                        mic_part = mic_buffer[:need]
                        mic_buffer = mic_buffer[need:]
                    else:
                        mic_part = mic_buffer
                        mic_buffer = np.empty((0,), dtype=np.int16)
                        if mic_part.size < need:
                            mic_part = np.pad(mic_part, (0, need - mic_part.size))

                    sys_f = sys_np.astype(np.float32) * float(self._sys_gain)
                    mic_f = mic_part.astype(np.float32) * float(self._mic_gain)
                    sys_scaled = sys_f.astype(np.int32)
                    mic_scaled = mic_f.astype(np.int32)
                    mixed = np.clip(sys_scaled + mic_scaled, -32768, 32767).astype(np.int16)
                    pcm_chunk = mixed.tobytes()
                    wf.writeframes(pcm_chunk)
                else:
                    pcm_chunk = chunk
                    wf.writeframes(pcm_chunk)

                if self._on_chunk is not None:
                    try:
                        self._on_chunk(pcm_chunk)
                    except Exception as exc:
                        logger.warning("Audio chunk callback error: %s", exc)

                with self._lock:
                    self._total_frames += len(chunk) // (sampwidth * self._channels)

        except Exception as exc:
            self._error = str(exc)
            logger.error("Recording thread error: %s", exc)
        finally:
            try:
                if recorder.is_recording():
                    recorder.stop_recording()
            except Exception:
                pass
            self._stop_event.set()
            if mic_thread is not None:
                try:
                    mic_thread.join(timeout=1.0)
                except Exception:
                    pass
            if wf is not None:
                try:
                    wf.close()
                except Exception:
                    pass

    def _start_mic_capture(self, mic_q: "queue.Queue[bytes]") -> Optional[threading.Thread]:
        """Start mic capture in a daemon thread."""
        try:
            import sounddevice as sd
        except ImportError:
            logger.warning(
                "sounddevice not installed - mic capture disabled. "
                "Install with: pip install sounddevice"
            )
            return None

        stop_event = self._stop_event
        sample_rate = self._sample_rate
        channels = self._channels

        mic_device = self._pick_mic_device(sd)
        if mic_device is not None:
            try:
                dev = sd.query_devices(mic_device)
                logger.info("Mic device [%s]: %s", mic_device, dev.get("name"))
            except Exception:
                logger.info("Mic device [%s]", mic_device)
        else:
            logger.info("Mic device: system default")

        def _mic_callback(indata, frames, time_info, status):  # noqa: ARG001
            if stop_event.is_set():
                raise sd.CallbackStop()
            try:
                mic_q.put_nowait(indata.tobytes())
            except queue.Full:
                pass

        def _run():
            try:
                with sd.InputStream(
                    samplerate=sample_rate,
                    channels=channels,
                    dtype="int16",
                    callback=_mic_callback,
                    blocksize=0,
                    device=mic_device,
                ):
                    while not stop_event.is_set():
                        sd.sleep(100)
            except Exception as exc:
                logger.error("Mic capture error: %s", exc)

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        return t

    @staticmethod
    def _pick_mic_device(sd) -> Optional[int]:
        """Heuristic mic device selection - prefer default / headset."""
        try:
            devices = sd.query_devices()
        except Exception:
            return None

        default_in = None
        try:
            default_in = sd.default.device[0]
        except Exception:
            pass

        keywords_headset = (
            "headset", "headphone", "earbud", "earphones",
            "airpods", "bluetooth", "bt", "usb", "wireless", "hands-free",
        )

        candidates: list[tuple[tuple[int, int, int, int], int]] = []
        for idx, d in enumerate(devices):
            try:
                max_in = int(d.get("max_input_channels") or 0)
            except Exception:
                max_in = 0
            if max_in <= 0:
                continue

            name = str(d.get("name") or "").lower()
            is_default = 1 if (default_in is not None and idx == default_in) else 0
            is_headset = 1 if any(k in name for k in keywords_headset) else 0
            channel_fit = 1 if max_in >= 1 else 0

            key = (is_default, is_headset, channel_fit, max_in)
            candidates.append((key, idx))

        if not candidates:
            return default_in

        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]
