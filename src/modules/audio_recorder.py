"""
System audio recorder module.

Captures system audio (via pysysaudio) with optional microphone mixing and
writes the result to a WAV file. Designed to be started / stopped
programmatically from the desktop UI rather than via Ctrl+C.
"""
import datetime as dt
import os
import queue
import threading
import time
import wave
from typing import Callable, List, Optional

import numpy as np

from src.config import (
    AUDIO_CHANNELS,
    AUDIO_MIC_ENABLED,
    AUDIO_MIC_GAIN,
    AUDIO_OUTPUT_DIR,
    AUDIO_SAMPLE_RATE,
    AUDIO_SYS_GAIN,
    TRANSCRIPTION_CHUNK_SECONDS,
    get_logger,
)

logger = get_logger(__name__)


class AudioRecorder:
    """Record system audio (+ optional mic) to a WAV file in a background thread.

    Supports chunk rotation every `chunk_seconds` seconds. Completed chunks
    are added to an internal queue accessible via `get_completed_chunks()`.
    """

    def __init__(
        self,
        sample_rate: int = AUDIO_SAMPLE_RATE,
        channels: int = AUDIO_CHANNELS,
        mic_enabled: bool = AUDIO_MIC_ENABLED,
        mic_gain: float = AUDIO_MIC_GAIN,
        sys_gain: float = AUDIO_SYS_GAIN,
        output_dir: str = AUDIO_OUTPUT_DIR,
        chunk_seconds: int = TRANSCRIPTION_CHUNK_SECONDS,
        on_chunk_complete: Optional[Callable[[str], None]] = None,
    ) -> None:
        self._sample_rate = sample_rate
        self._channels = channels
        self._mic_enabled = mic_enabled
        self._mic_gain = mic_gain
        self._sys_gain = sys_gain
        self._output_dir = output_dir
        self._chunk_seconds = chunk_seconds
        self._on_chunk_complete = on_chunk_complete

        # Internal state
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._output_path: Optional[str] = None
        self._start_time: Optional[float] = None
        self._error: Optional[str] = None
        self._total_frames: int = 0
        self._lock = threading.Lock()
        self._completed_chunks: List[str] = []
        self._chunk_index: int = 0

    # ── Public API ────────────────────────────────────────────────────────

    @property
    def is_recording(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def elapsed_seconds(self) -> float:
        if self._start_time is None:
            return 0.0
        return time.time() - self._start_time

    @property
    def output_path(self) -> Optional[str]:
        return self._output_path

    @property
    def error(self) -> Optional[str]:
        return self._error

    def get_completed_chunks(self) -> List[str]:
        """Trả về danh sách đường dẫn các chunk đã hoàn thành (thread-safe)."""
        with self._lock:
            return list(self._completed_chunks)

    def start(self, output_path: Optional[str] = None) -> str:
        """
        Begin recording. Returns the output WAV path.

        Raises RuntimeError if already recording.
        """
        if self.is_recording:
            raise RuntimeError("Already recording.")

        if output_path is None:
            ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
            os.makedirs(self._output_dir, exist_ok=True)
            output_path = os.path.join(self._output_dir, f"system_audio_{ts}.wav")

        self._output_path = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(self._output_path), exist_ok=True)

        self._stop_event.clear()
        self._error = None
        self._total_frames = 0
        self._chunk_index = 0
        with self._lock:
            self._completed_chunks = []

        self._thread = threading.Thread(target=self._record_loop, daemon=True)
        self._thread.start()

        self._start_time = time.time()
        logger.info("Recording started → %s", self._output_path)
        return self._output_path

    def stop(self) -> str:
        """
        Stop recording and return the WAV path.

        Raises RuntimeError if not currently recording or if the recording
        thread encountered an error.
        """
        if not self.is_recording:
            raise RuntimeError("Not recording.")

        self._stop_event.set()
        self._thread.join(timeout=5.0)
        self._thread = None
        self._start_time = None

        if self._error:
            raise RuntimeError(f"Recording failed: {self._error}")

        duration = self._total_frames / float(self._sample_rate) if self._sample_rate else 0
        logger.info(
            "Recording stopped. Frames: %d | Duration: %.2fs | File: %s",
            self._total_frames, duration, self._output_path,
        )
        return self._output_path

    # ── Recording loop (runs in background thread) ────────────────────────

    def _chunk_path(self, index: int) -> str:
        """Tính đường dẫn file cho chunk index."""
        base = os.path.splitext(self._output_path)[0]
        return f"{base}_chunk{index:03d}.wav"

    def _open_wav(self, path: str, sampwidth: int) -> wave.Wave_write:
        wf = wave.open(path, "wb")
        wf.setnchannels(self._channels)
        wf.setsampwidth(sampwidth)
        wf.setframerate(self._sample_rate)
        wf.setcomptype("NONE", "not compressed")
        return wf

    def _finish_chunk(self, wf: wave.Wave_write, path: str) -> None:
        """Đóng chunk file và thêm vào danh sách completed."""
        try:
            wf.close()
        except Exception:
            pass
        with self._lock:
            self._completed_chunks.append(path)
        logger.info("Chunk hoàn tất: %s", path)
        if self._on_chunk_complete:
            try:
                self._on_chunk_complete(path)
            except Exception as exc:
                logger.warning("on_chunk_complete callback lỗi: %s", exc)

    def _record_loop(self) -> None:  # noqa: C901
        """Capture system audio, optionally mix mic, write WAV với chunk rotation."""
        from pysysaudio import SystemAudioRecorder as SysRecorder

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
        current_chunk_path: Optional[str] = None

        try:
            current_chunk_path = self._chunk_path(self._chunk_index)
            wf = self._open_wav(current_chunk_path, sampwidth)
            chunk_start = time.time()

            # Optionally start mic capture
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
                    # Drain mic queue into rolling buffer
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

                    sys_scaled = (sys_np.astype(np.float32) * float(self._sys_gain)).astype(np.int32)
                    mic_scaled = (mic_part.astype(np.float32) * float(self._mic_gain)).astype(np.int32)
                    mixed = np.clip(sys_scaled + mic_scaled, -32768, 32767).astype(np.int16)
                    wf.writeframes(mixed.tobytes())
                else:
                    wf.writeframes(chunk)

                with self._lock:
                    self._total_frames += len(chunk) // (sampwidth * self._channels)

                # Chunk rotation: khi đủ chunk_seconds, đóng file và mở chunk mới
                if time.time() - chunk_start >= self._chunk_seconds:
                    self._finish_chunk(wf, current_chunk_path)
                    self._chunk_index += 1
                    current_chunk_path = self._chunk_path(self._chunk_index)
                    wf = self._open_wav(current_chunk_path, sampwidth)
                    chunk_start = time.time()

        except Exception as exc:
            self._error = str(exc)
            logger.error("Recording thread error: %s", exc)
        finally:
            try:
                if recorder.is_recording():
                    recorder.stop_recording()
            except Exception:
                pass
            self._stop_event.set()  # signal mic thread too
            if mic_thread is not None:
                try:
                    mic_thread.join(timeout=1.0)
                except Exception:
                    pass
            if wf is not None and current_chunk_path is not None:
                self._finish_chunk(wf, current_chunk_path)

    # ── Mic capture helper ────────────────────────────────────────────────

    def _start_mic_capture(self, mic_q: "queue.Queue[bytes]") -> threading.Thread:
        """Start mic capture in a daemon thread. Returns the thread object."""
        try:
            import sounddevice as sd
        except ImportError:
            logger.warning(
                "sounddevice not installed — mic capture disabled. "
                "Install with: pip install sounddevice"
            )
            return None  # type: ignore[return-value]

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
                pass  # drop if consumer is slow

        def _run():
            try:
                with sd.InputStream(
                    samplerate=sample_rate,
                    channels=channels,
                    dtype="int16",
                    callback=_mic_callback,
                    blocksize=0,
                    device=mic_device,
                ) as _stream:
                    while not stop_event.is_set():
                        sd.sleep(100)
            except Exception as exc:
                logger.error("Mic capture error: %s", exc)

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        return t

    @staticmethod
    def _pick_mic_device(sd) -> Optional[int]:
        """Heuristic mic device selection — prefer default / headset."""
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
