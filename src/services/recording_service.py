"""
Recording service — orchestrate AudioRecorder for the Streamlit app.
"""
from typing import Optional

from src.config import (
    AUDIO_CHANNELS,
    AUDIO_MIC_ENABLED,
    AUDIO_MIC_GAIN,
    AUDIO_OUTPUT_DIR,
    AUDIO_SAMPLE_RATE,
    AUDIO_SYS_GAIN,
    get_logger,
)
from src.modules.audio_recorder import AudioRecorder

logger = get_logger(__name__)

# Module-level singleton so Streamlit reruns don't lose the recorder.
_recorder: Optional[AudioRecorder] = None


def get_recorder() -> AudioRecorder:
    """Return (or create) the module-level AudioRecorder singleton."""
    global _recorder
    if _recorder is None:
        _recorder = AudioRecorder(
            sample_rate=AUDIO_SAMPLE_RATE,
            channels=AUDIO_CHANNELS,
            mic_enabled=AUDIO_MIC_ENABLED,
            mic_gain=AUDIO_MIC_GAIN,
            sys_gain=AUDIO_SYS_GAIN,
            output_dir=AUDIO_OUTPUT_DIR,
        )
    return _recorder


def start_recording(output_path: Optional[str] = None) -> str:
    """
    Start recording system audio.

    Returns the WAV output path.
    """
    recorder = get_recorder()
    path = recorder.start(output_path=output_path)
    logger.info("Recording service: started → %s", path)
    return path


def stop_recording() -> str:
    """
    Stop recording and return the WAV path.

    Raises RuntimeError if not currently recording.
    """
    recorder = get_recorder()
    path = recorder.stop()
    logger.info("Recording service: stopped → %s", path)
    return path


def is_recording() -> bool:
    """Check whether a recording is in progress."""
    recorder = get_recorder()
    return recorder.is_recording


def elapsed_seconds() -> float:
    """Seconds elapsed since recording started."""
    recorder = get_recorder()
    return recorder.elapsed_seconds
