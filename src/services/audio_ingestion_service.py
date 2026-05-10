"""
Audio ingestion service — Task 1.1-B.2
========================================
Xử lý file upload: validate → normalize/extract → lưu trữ.

Supported audio: .mp3, .wav, .m4a, .ogg
Supported video: .mp4, .mkv, .webm

Output: WAV 16kHz mono (Whisper optimal format).
"""

from __future__ import annotations

import os
import shutil
import tempfile
import uuid
import wave
from pathlib import Path
from typing import BinaryIO, Optional, Union

import ffmpeg

from src.config import get_logger, get_settings

logger = get_logger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

ALLOWED_AUDIO_EXTENSIONS = frozenset({".mp3", ".wav", ".m4a", ".ogg"})
ALLOWED_VIDEO_EXTENSIONS = frozenset({".mp4", ".mkv", ".webm"})
ALLOWED_EXTENSIONS = ALLOWED_AUDIO_EXTENSIONS | ALLOWED_VIDEO_EXTENSIONS

WHISPER_SAMPLE_RATE = 16_000
WHISPER_CHANNELS = 1  # mono

# ── Exceptions ────────────────────────────────────────────────────────────────


class UnsupportedFileFormat(ValueError):
    """Raised when the uploaded file has an unsupported extension."""


class FileTooLarge(ValueError):
    """Raised when the uploaded file exceeds the size limit."""


class AudioProcessingError(RuntimeError):
    """Raised when ffmpeg fails to process the file."""


# ── Validation ────────────────────────────────────────────────────────────────


def validate_upload(
    filename: str,
    file_size: Optional[int] = None,
) -> str:
    """Validate the uploaded file format and size.

    Args:
        filename: Original filename from the upload.
        file_size: File size in bytes (if known).

    Returns:
        The lowercase file extension (e.g. ``".mp3"``).

    Raises:
        UnsupportedFileFormat: If the extension is not allowed.
        FileTooLarge: If the file exceeds the configured max size.
    """
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise UnsupportedFileFormat(
            f"Unsupported file format '{ext}'. "
            f"Allowed: {sorted(ALLOWED_EXTENSIONS)}"
        )

    if file_size is not None:
        settings = get_settings()
        max_bytes = settings.audio_max_upload_mb * 1024 * 1024
        if file_size > max_bytes:
            raise FileTooLarge(
                f"File size ({file_size / 1024 / 1024:.1f} MB) exceeds "
                f"limit ({settings.audio_max_upload_mb} MB)."
            )

    return ext


def is_video_extension(ext: str) -> bool:
    """Check if the extension belongs to a video format."""
    return ext.lower() in ALLOWED_VIDEO_EXTENSIONS


# ── Audio Processing ──────────────────────────────────────────────────────────


def normalize_audio(input_path: str, output_path: str) -> str:
    """Convert any audio file to WAV 16kHz mono (Whisper optimal).

    Args:
        input_path: Path to the source audio file.
        output_path: Path for the output WAV file.

    Returns:
        The output path.

    Raises:
        AudioProcessingError: If ffmpeg conversion fails.
    """
    try:
        (
            ffmpeg
            .input(input_path)
            .output(
                output_path,
                ar=WHISPER_SAMPLE_RATE,
                ac=WHISPER_CHANNELS,
                acodec="pcm_s16le",
                f="wav",
            )
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
    except ffmpeg.Error as exc:
        stderr = exc.stderr.decode() if exc.stderr else "unknown error"
        raise AudioProcessingError(
            f"Failed to normalize audio: {stderr}"
        ) from exc

    logger.info("Normalized audio → %s (16kHz mono WAV)", output_path)
    return output_path


def extract_audio_from_video(video_path: str, output_path: str) -> str:
    """Extract audio track from a video file and normalize to WAV 16kHz mono.

    Args:
        video_path: Path to the source video file.
        output_path: Path for the output WAV file.

    Returns:
        The output path.

    Raises:
        AudioProcessingError: If ffmpeg extraction/conversion fails.
    """
    try:
        (
            ffmpeg
            .input(video_path)
            .output(
                output_path,
                ar=WHISPER_SAMPLE_RATE,
                ac=WHISPER_CHANNELS,
                acodec="pcm_s16le",
                f="wav",
                vn=None,  # no video
            )
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
    except ffmpeg.Error as exc:
        stderr = exc.stderr.decode() if exc.stderr else "unknown error"
        raise AudioProcessingError(
            f"Failed to extract audio from video: {stderr}"
        ) from exc

    logger.info("Extracted audio from video → %s", output_path)
    return output_path


def get_audio_duration(wav_path: str) -> float:
    """Get the duration of a WAV file in seconds.

    Args:
        wav_path: Path to a WAV file.

    Returns:
        Duration in seconds.

    Raises:
        AudioProcessingError: If the file cannot be read.
    """
    try:
        with wave.open(wav_path, "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            if rate <= 0:
                raise AudioProcessingError(f"Invalid sample rate: {rate}")
            return frames / float(rate)
    except wave.Error as exc:
        raise AudioProcessingError(
            f"Failed to read WAV duration: {exc}"
        ) from exc


# ── High-level orchestrator ───────────────────────────────────────────────────


def build_storage_path(user_id: Union[str, uuid.UUID], meeting_id: str) -> str:
    """Build the canonical storage path for a meeting's audio.

    Format: ``meeting-audio/{user_id}/{meeting_id}.wav``

    Args:
        user_id: The user ID.
        meeting_id: The meeting UUID string.

    Returns:
        Relative storage path string.
    """
    user_id_str = str(user_id)
    return f"meeting-audio/{user_id_str}/{meeting_id}.wav"


def process_upload(
    file_stream: BinaryIO,
    filename: str,
    user_id: Union[str, uuid.UUID],
    meeting_id: str,
    file_size: Optional[int] = None,
) -> tuple[str, str, float]:
    """Process an uploaded audio/video file end-to-end.

    Pipeline: validate → save temp → normalize/extract → move to storage → get duration

    Args:
        file_stream: File-like object of the upload.
        filename: Original filename.
        user_id: Owner user ID.
        meeting_id: Meeting UUID string.
        file_size: File size in bytes (optional).

    Returns:
        Tuple of (absolute_wav_path, relative_storage_path, duration_seconds).

    Raises:
        UnsupportedFileFormat: If format is invalid.
        FileTooLarge: If file is too large.
        AudioProcessingError: If conversion fails.
    """
    ext = validate_upload(filename, file_size)
    settings = get_settings()

    # Build output paths
    user_id_str = str(user_id)
    storage_path = build_storage_path(user_id_str, meeting_id)
    abs_output_dir = os.path.join(settings.audio_storage_base, user_id_str)
    os.makedirs(abs_output_dir, exist_ok=True)
    abs_output_path = os.path.join(abs_output_dir, f"{meeting_id}.wav")

    # Save uploaded file to a temporary location
    tmp_dir = os.path.join(settings.audio_storage_base, ".tmp")
    os.makedirs(tmp_dir, exist_ok=True)

    tmp_suffix = ext
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=tmp_suffix, dir=tmp_dir)
    try:
        with os.fdopen(tmp_fd, "wb") as tmp_f:
            shutil.copyfileobj(file_stream, tmp_f)

        # Process: normalize or extract
        if is_video_extension(ext):
            extract_audio_from_video(tmp_path, abs_output_path)
        else:
            normalize_audio(tmp_path, abs_output_path)

    finally:
        # Clean up temp file
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    # Get duration
    duration = get_audio_duration(abs_output_path)

    logger.info(
        "File ingestion complete: user=%s meeting=%s duration=%.1fs path=%s",
        user_id_str, meeting_id, duration, abs_output_path,
    )

    return abs_output_path, storage_path, duration
