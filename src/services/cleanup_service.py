"""
Cleanup service - manage audio file retention and cleanup.

Handles:
- Immediate deletion after successful transcription
- Scheduled cleanup of old/failed recordings
- Retention policy based on AUDIO_RETENTION_HOURS setting
"""
import datetime as dt
import re
from pathlib import Path
from typing import Optional

from src.config import get_logger, get_settings

logger = get_logger(__name__)

TIMESTAMP_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}")


def delete_audio_file(audio_path: str) -> bool:
    """
    Delete an audio file after successful processing.

    Args:
        audio_path: Path to the audio file to delete.

    Returns:
        True if file was deleted, False if it didn't exist or deletion failed.
    """
    try:
        path = Path(audio_path)
        if path.exists():
            path.unlink()
            logger.info("Deleted audio file: %s", audio_path)
            return True
        logger.debug("Audio file not found for deletion: %s", audio_path)
        return False
    except Exception as exc:
        logger.error("Failed to delete audio file %s: %s", audio_path, exc)
        return False


def cleanup_old_recordings(
    output_dir: Optional[str] = None,
    retention_hours: Optional[int] = None,
) -> int:
    """
    Clean up old recordings based on retention policy.

    Files older than retention_hours are deleted.
    Files with timestamp patterns in their names are checked against that timestamp.
    Other files use file modification time.

    Args:
        output_dir: Directory to clean. If None, uses settings.
        retention_hours: Hours to retain files. If None, uses settings.
            If 0, no automatic cleanup (files deleted only via delete_audio_file).

    Returns:
        Number of files deleted.
    """
    settings = get_settings()
    dir_path = Path(output_dir if output_dir is not None else settings.audio_output_dir)
    hours = retention_hours if retention_hours is not None else settings.audio_retention_hours

    if hours == 0:
        logger.debug("Retention hours is 0 - skipping automatic cleanup.")
        return 0

    if not dir_path.exists():
        logger.debug("Output directory does not exist: %s", dir_path)
        return 0

    cutoff = dt.datetime.now() - dt.timedelta(hours=hours)
    deleted_count = 0

    for file_path in dir_path.iterdir():
        if not file_path.is_file():
            continue

        if not file_path.suffix.lower() in (".wav", ".mp3", ".m4a", ".flac", ".ogg", ".webm"):
            continue

        file_time = _get_file_timestamp(file_path)
        if file_time and file_time < cutoff:
            try:
                file_path.unlink()
                logger.info("Cleaned up old recording: %s", file_path)
                deleted_count += 1
            except Exception as exc:
                logger.error("Failed to delete old recording %s: %s", file_path, exc)

    if deleted_count > 0:
        logger.info("Cleanup complete: deleted %d files older than %d hours.", deleted_count, hours)

    return deleted_count


def _get_file_timestamp(file_path: Path) -> Optional[dt.datetime]:
    """
    Get timestamp for a file.

    First tries to extract from filename (YYYY-MM-DD_HH-MM-SS pattern).
    Falls back to file modification time.

    Args:
        file_path: Path to the file.

    Returns:
        Datetime of the file, or None if cannot be determined.
    """
    match = TIMESTAMP_PATTERN.search(file_path.stem)
    if match:
        try:
            timestamp_str = match.group()
            return dt.datetime.strptime(timestamp_str, "%Y-%m-%d_%H-%M-%S")
        except ValueError:
            pass

    try:
        mtime = file_path.stat().st_mtime
        return dt.datetime.fromtimestamp(mtime)
    except Exception:
        return None


def generate_recording_filename(prefix: str = "recording", extension: str = ".wav") -> str:
    """
    Generate a timestamped filename for a recording.

    Format: {prefix}_{YYYY-MM-DD}_{HH-MM-SS}{extension}

    Args:
        prefix: Filename prefix (e.g., "recording", "failed").
        extension: File extension including dot (e.g., ".wav").

    Returns:
        Timestamped filename.
    """
    timestamp = dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return f"{prefix}_{timestamp}{extension}"


def get_recordings_summary(output_dir: Optional[str] = None) -> dict:
    """
    Get summary of recordings in the output directory.

    Args:
        output_dir: Directory to scan. If None, uses settings.

    Returns:
        Dict with counts and total size.
    """
    settings = get_settings()
    dir_path = Path(output_dir if output_dir is not None else settings.audio_output_dir)

    if not dir_path.exists():
        return {"count": 0, "total_size_mb": 0.0, "oldest": None, "newest": None}

    audio_extensions = (".wav", ".mp3", ".m4a", ".flac", ".ogg", ".webm")
    files = [f for f in dir_path.iterdir() if f.is_file() and f.suffix.lower() in audio_extensions]

    if not files:
        return {"count": 0, "total_size_mb": 0.0, "oldest": None, "newest": None}

    total_size = sum(f.stat().st_size for f in files)
    timestamps = [_get_file_timestamp(f) for f in files]
    valid_timestamps = [t for t in timestamps if t is not None]

    return {
        "count": len(files),
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "oldest": min(valid_timestamps).isoformat() if valid_timestamps else None,
        "newest": max(valid_timestamps).isoformat() if valid_timestamps else None,
    }
