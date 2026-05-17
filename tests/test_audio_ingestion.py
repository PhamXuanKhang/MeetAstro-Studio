"""
Unit tests for src/services/audio_ingestion_service.py — Task 1.1-B.2
======================================================================
Coverage:
    - validate_upload: accept/reject extensions, file size limits
    - is_video_extension: classify audio vs video
    - normalize_audio: ffmpeg WAV conversion (mocked)
    - extract_audio_from_video: ffmpeg video extraction (mocked)
    - get_audio_duration: real WAV file duration calculation
    - build_storage_path: path format
    - process_upload: end-to-end integration (mocked ffmpeg)
"""

from __future__ import annotations

import io
import os
import struct
import wave
from unittest.mock import MagicMock, patch

import pytest


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    """Clear settings cache before each test."""
    from src.config import clear_settings_cache
    clear_settings_cache()
    yield
    clear_settings_cache()


def _create_wav_file(path: str, duration_secs: float = 2.0, sample_rate: int = 16000) -> str:
    """Create a minimal valid WAV file for testing."""
    n_frames = int(sample_rate * duration_secs)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # int16
        wf.setframerate(sample_rate)
        # Write silence (zeros)
        wf.writeframes(b"\x00\x00" * n_frames)
    return path


# ── validate_upload tests ─────────────────────────────────────────────────────


class TestValidateUpload:
    def test_accept_mp3(self):
        from src.services.audio_ingestion_service import validate_upload
        assert validate_upload("recording.mp3") == ".mp3"

    def test_accept_wav(self):
        from src.services.audio_ingestion_service import validate_upload
        assert validate_upload("audio.WAV") == ".wav"

    def test_accept_m4a(self):
        from src.services.audio_ingestion_service import validate_upload
        assert validate_upload("voice.m4a") == ".m4a"

    def test_accept_ogg(self):
        from src.services.audio_ingestion_service import validate_upload
        assert validate_upload("podcast.ogg") == ".ogg"

    def test_accept_mp4_video(self):
        from src.services.audio_ingestion_service import validate_upload
        assert validate_upload("meeting.mp4") == ".mp4"

    def test_accept_mkv_video(self):
        from src.services.audio_ingestion_service import validate_upload
        assert validate_upload("screen.mkv") == ".mkv"

    def test_accept_webm_video(self):
        from src.services.audio_ingestion_service import validate_upload
        assert validate_upload("call.webm") == ".webm"

    def test_reject_txt(self):
        from src.services.audio_ingestion_service import validate_upload, UnsupportedFileFormat
        with pytest.raises(UnsupportedFileFormat, match="Unsupported"):
            validate_upload("notes.txt")

    def test_reject_pdf(self):
        from src.services.audio_ingestion_service import validate_upload, UnsupportedFileFormat
        with pytest.raises(UnsupportedFileFormat, match="Unsupported"):
            validate_upload("document.pdf")

    def test_reject_exe(self):
        from src.services.audio_ingestion_service import validate_upload, UnsupportedFileFormat
        with pytest.raises(UnsupportedFileFormat, match="Unsupported"):
            validate_upload("virus.exe")

    def test_reject_no_extension(self):
        from src.services.audio_ingestion_service import validate_upload, UnsupportedFileFormat
        with pytest.raises(UnsupportedFileFormat):
            validate_upload("noextension")

    def test_file_too_large(self, monkeypatch):
        from src.services.audio_ingestion_service import validate_upload, FileTooLarge
        monkeypatch.setenv("AUDIO_MAX_UPLOAD_MB", "1")
        from src.config import clear_settings_cache
        clear_settings_cache()
        # 2 MB > 1 MB limit
        with pytest.raises(FileTooLarge, match="exceeds"):
            validate_upload("audio.mp3", file_size=2 * 1024 * 1024)

    def test_file_within_limit(self, monkeypatch):
        from src.services.audio_ingestion_service import validate_upload
        monkeypatch.setenv("AUDIO_MAX_UPLOAD_MB", "10")
        from src.config import clear_settings_cache
        clear_settings_cache()
        # 5 MB < 10 MB limit — should pass
        assert validate_upload("audio.mp3", file_size=5 * 1024 * 1024) == ".mp3"

    def test_file_size_none_skips_check(self):
        from src.services.audio_ingestion_service import validate_upload
        # No file_size → no size check
        assert validate_upload("audio.mp3", file_size=None) == ".mp3"


# ── is_video_extension tests ──────────────────────────────────────────────────


class TestIsVideoExtension:
    def test_mp4_is_video(self):
        from src.services.audio_ingestion_service import is_video_extension
        assert is_video_extension(".mp4") is True

    def test_mkv_is_video(self):
        from src.services.audio_ingestion_service import is_video_extension
        assert is_video_extension(".mkv") is True

    def test_webm_is_video(self):
        from src.services.audio_ingestion_service import is_video_extension
        assert is_video_extension(".webm") is True

    def test_mp3_is_not_video(self):
        from src.services.audio_ingestion_service import is_video_extension
        assert is_video_extension(".mp3") is False

    def test_wav_is_not_video(self):
        from src.services.audio_ingestion_service import is_video_extension
        assert is_video_extension(".wav") is False


# ── get_audio_duration tests ──────────────────────────────────────────────────


class TestGetAudioDuration:
    def test_duration_correct(self, tmp_path):
        from src.services.audio_ingestion_service import get_audio_duration
        wav_path = str(tmp_path / "test.wav")
        _create_wav_file(wav_path, duration_secs=3.0, sample_rate=16000)
        duration = get_audio_duration(wav_path)
        assert abs(duration - 3.0) < 0.01

    def test_short_duration(self, tmp_path):
        from src.services.audio_ingestion_service import get_audio_duration
        wav_path = str(tmp_path / "short.wav")
        _create_wav_file(wav_path, duration_secs=0.5, sample_rate=16000)
        duration = get_audio_duration(wav_path)
        assert abs(duration - 0.5) < 0.01

    def test_invalid_file_raises(self, tmp_path):
        from src.services.audio_ingestion_service import get_audio_duration, AudioProcessingError
        bad_file = tmp_path / "bad.wav"
        bad_file.write_text("this is not a wav file")
        with pytest.raises(AudioProcessingError, match="duration"):
            get_audio_duration(str(bad_file))


# ── build_storage_path tests ─────────────────────────────────────────────────


class TestBuildStoragePath:
    def test_format(self):
        from src.services.audio_ingestion_service import build_storage_path
        path = build_storage_path("user123", "abc-def-ghi")
        assert path == "meeting-audio/user123/abc-def-ghi.wav"

    def test_default_user(self):
        from src.services.audio_ingestion_service import build_storage_path
        path = build_storage_path("default_user", "meeting-uuid")
        assert path == "meeting-audio/default_user/meeting-uuid.wav"


# ── normalize_audio tests (mocked ffmpeg) ─────────────────────────────────────


class TestNormalizeAudio:
    @patch("src.services.audio_ingestion_service.ffmpeg")
    def test_calls_ffmpeg_correctly(self, mock_ffmpeg):
        from src.services.audio_ingestion_service import normalize_audio

        # Setup chain mock
        mock_input = MagicMock()
        mock_ffmpeg.input.return_value = mock_input
        mock_output = MagicMock()
        mock_input.output.return_value = mock_output
        mock_overwrite = MagicMock()
        mock_output.overwrite_output.return_value = mock_overwrite

        result = normalize_audio("/tmp/input.mp3", "/tmp/output.wav")

        mock_ffmpeg.input.assert_called_once_with("/tmp/input.mp3")
        mock_input.output.assert_called_once_with(
            "/tmp/output.wav",
            ar=16000,
            ac=1,
            acodec="pcm_s16le",
            f="wav",
        )
        mock_overwrite.run.assert_called_once()
        assert result == "/tmp/output.wav"

    @patch("src.services.audio_ingestion_service.ffmpeg")
    def test_raises_on_ffmpeg_error(self, mock_ffmpeg):
        from src.services.audio_ingestion_service import normalize_audio, AudioProcessingError
        import ffmpeg as ffmpeg_lib

        mock_input = MagicMock()
        mock_ffmpeg.input.return_value = mock_input
        mock_output = MagicMock()
        mock_input.output.return_value = mock_output
        mock_overwrite = MagicMock()
        mock_output.overwrite_output.return_value = mock_overwrite
        mock_overwrite.run.side_effect = ffmpeg_lib.Error("ffmpeg", b"", b"conversion failed")

        # Also patch the Error class on the mocked module
        mock_ffmpeg.Error = ffmpeg_lib.Error

        with pytest.raises(AudioProcessingError, match="normalize"):
            normalize_audio("/tmp/bad.mp3", "/tmp/output.wav")


# ── extract_audio_from_video tests (mocked ffmpeg) ───────────────────────────


class TestExtractAudioFromVideo:
    @patch("src.services.audio_ingestion_service.ffmpeg")
    def test_calls_ffmpeg_with_vn(self, mock_ffmpeg):
        from src.services.audio_ingestion_service import extract_audio_from_video

        mock_input = MagicMock()
        mock_ffmpeg.input.return_value = mock_input
        mock_output = MagicMock()
        mock_input.output.return_value = mock_output
        mock_overwrite = MagicMock()
        mock_output.overwrite_output.return_value = mock_overwrite

        result = extract_audio_from_video("/tmp/video.mp4", "/tmp/audio.wav")

        mock_input.output.assert_called_once_with(
            "/tmp/audio.wav",
            ar=16000,
            ac=1,
            acodec="pcm_s16le",
            f="wav",
            vn=None,
        )
        assert result == "/tmp/audio.wav"


# ── process_upload integration tests ──────────────────────────────────────────


class TestProcessUpload:
    @patch("src.services.audio_ingestion_service.normalize_audio")
    def test_audio_upload_end_to_end(self, mock_normalize, tmp_path, monkeypatch):
        from src.services.audio_ingestion_service import process_upload
        from src.config import clear_settings_cache

        # Setup: point storage to tmp_path
        storage_base = str(tmp_path / "storage")
        monkeypatch.setenv("AUDIO_STORAGE_BASE", storage_base)
        clear_settings_cache()

        # Create a fake WAV that normalize_audio will "produce"
        def fake_normalize(input_path, output_path):
            _create_wav_file(output_path, duration_secs=5.0)
            return output_path
        mock_normalize.side_effect = fake_normalize

        # Create a fake upload stream
        file_stream = io.BytesIO(b"fake mp3 data")

        vps_path, duration = process_upload(
            file_stream=file_stream,
            filename="meeting.mp3",
            user_id="test_user",
            meeting_id="uuid-1234",
        )

        # The returned path is a random temp file in .tmp/ dir (not the meeting_id)
        assert vps_path.endswith(".mp3")
        assert ".tmp" in vps_path
        assert os.path.exists(vps_path)
        assert abs(duration - 5.0) < 0.01
        mock_normalize.assert_called_once()

    @patch("src.services.audio_ingestion_service.extract_audio_from_video")
    def test_video_upload_extracts_audio(self, mock_extract, tmp_path, monkeypatch):
        from src.services.audio_ingestion_service import process_upload
        from src.config import clear_settings_cache

        storage_base = str(tmp_path / "storage")
        monkeypatch.setenv("AUDIO_STORAGE_BASE", storage_base)
        clear_settings_cache()

        def fake_extract(video_path, output_path):
            _create_wav_file(output_path, duration_secs=120.0)
            return output_path
        mock_extract.side_effect = fake_extract

        file_stream = io.BytesIO(b"fake mp4 data")

        vps_path, duration = process_upload(
            file_stream=file_stream,
            filename="recording.mp4",
            user_id="user_abc",
            meeting_id="uuid-5678",
        )

        assert abs(duration - 120.0) < 0.1
        mock_extract.assert_called_once()

    def test_reject_invalid_format(self):
        from src.services.audio_ingestion_service import process_upload, UnsupportedFileFormat

        with pytest.raises(UnsupportedFileFormat):
            process_upload(
                file_stream=io.BytesIO(b"data"),
                filename="document.pdf",
                user_id="user",
                meeting_id="id",
            )

    def test_reject_too_large(self, monkeypatch):
        from src.services.audio_ingestion_service import process_upload, FileTooLarge
        from src.config import clear_settings_cache

        monkeypatch.setenv("AUDIO_MAX_UPLOAD_MB", "1")
        clear_settings_cache()

        with pytest.raises(FileTooLarge):
            process_upload(
                file_stream=io.BytesIO(b"data"),
                filename="audio.mp3",
                user_id="user",
                meeting_id="id",
                file_size=2 * 1024 * 1024,
            )

    @patch("src.services.audio_ingestion_service.normalize_audio")
    def test_temp_file_cleaned_up(self, mock_normalize, tmp_path, monkeypatch):
        """Verify temporary files are cleaned up after processing."""
        from src.services.audio_ingestion_service import process_upload
        from src.config import clear_settings_cache

        storage_base = str(tmp_path / "storage")
        monkeypatch.setenv("AUDIO_STORAGE_BASE", storage_base)
        clear_settings_cache()

        def fake_normalize(input_path, output_path):
            _create_wav_file(output_path, duration_secs=1.0)
            return output_path
        mock_normalize.side_effect = fake_normalize

        file_stream = io.BytesIO(b"fake data")
        process_upload(
            file_stream=file_stream,
            filename="test.wav",
            user_id="user",
            meeting_id="mid",
        )

        # tmp dir should contain the returned vps_path (kept for pipeline to consume)
        tmp_dir = os.path.join(storage_base, ".tmp")
        if os.path.exists(tmp_dir):
            assert len(os.listdir(tmp_dir)) == 1

    @patch("src.services.audio_ingestion_service.normalize_audio")
    def test_temp_file_cleaned_up_on_error(self, mock_normalize, tmp_path, monkeypatch):
        """Verify temp files are cleaned even when processing fails."""
        from src.services.audio_ingestion_service import process_upload, AudioProcessingError
        from src.config import clear_settings_cache

        storage_base = str(tmp_path / "storage")
        monkeypatch.setenv("AUDIO_STORAGE_BASE", storage_base)
        clear_settings_cache()

        mock_normalize.side_effect = AudioProcessingError("boom")

        file_stream = io.BytesIO(b"fake data")
        with pytest.raises(AudioProcessingError):
            process_upload(
                file_stream=file_stream,
                filename="test.ogg",
                user_id="user",
                meeting_id="mid",
            )

        tmp_dir = os.path.join(storage_base, ".tmp")
        if os.path.exists(tmp_dir):
            assert len(os.listdir(tmp_dir)) == 0
