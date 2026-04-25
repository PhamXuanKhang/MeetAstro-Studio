"""Recording service - orchestrate AudioRecorder for the desktop app."""
from typing import Optional

from src.config import get_logger, get_settings
from src.modules.audio_recorder import AudioRecorder

logger = get_logger(__name__)

_recorder: Optional[AudioRecorder] = None


def get_recorder() -> AudioRecorder:
    """Return (or create) the module-level AudioRecorder singleton."""
    global _recorder
    if _recorder is None:
        settings = get_settings()
        _recorder = AudioRecorder(
            sample_rate=settings.audio_sample_rate,
            channels=settings.audio_channels,
            mic_enabled=settings.audio_mic_enabled,
            mic_gain=settings.audio_mic_gain,
            sys_gain=settings.audio_sys_gain,
            output_dir=settings.audio_output_dir,
        )
    return _recorder


def reset_recorder() -> None:
    """Reset the recorder singleton. Useful for testing."""
    global _recorder
    _recorder = None


def start_recording(output_path: Optional[str] = None) -> str:
    """
    Start recording system audio.

    Args:
        output_path: Optional custom output path.

    Returns:
        The WAV output path.
    """
    recorder = get_recorder()
    path = recorder.start(output_path=output_path)
    logger.info("Recording service: started -> %s", path)
    return path


def stop_recording() -> str:
    """
    Stop recording and return the WAV path.

    Returns:
        The WAV output path.

    Raises:
        RuntimeError: If not currently recording.
    """
    recorder = get_recorder()
    path = recorder.stop()
    logger.info("Recording service: stopped -> %s", path)
    return path


def is_recording() -> bool:
    """Check whether a recording is in progress."""
    recorder = get_recorder()
    return recorder.is_recording
