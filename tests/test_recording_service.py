"""Tests cho chunked recording — mock AudioRecorder, verify chunk API."""
from unittest.mock import MagicMock, patch

import pytest

import src.services.recording_service as svc


def _make_mock_recorder(chunks=None):
    mock = MagicMock()
    mock.is_recording = False
    mock.elapsed_seconds = 0.0
    mock.get_completed_chunks.return_value = chunks or []
    mock.start.return_value = "/tmp/audio_chunk000.wav"
    mock.stop.return_value = "/tmp/audio_chunk000.wav"
    return mock


class TestGetCompletedChunks:
    def test_returns_empty_before_recording(self):
        mock_rec = _make_mock_recorder(chunks=[])
        with patch("src.services.recording_service._recorder", mock_rec):
            result = svc.get_completed_chunks()
        assert result == []

    def test_returns_chunk_paths(self):
        paths = ["/tmp/chunk000.wav", "/tmp/chunk001.wav"]
        mock_rec = _make_mock_recorder(chunks=paths)
        with patch("src.services.recording_service._recorder", mock_rec):
            result = svc.get_completed_chunks()
        assert result == paths

    def test_delegates_to_recorder(self):
        mock_rec = _make_mock_recorder()
        with patch("src.services.recording_service._recorder", mock_rec):
            svc.get_completed_chunks()
        mock_rec.get_completed_chunks.assert_called_once()


class TestAudioRecorderChunkAPI:
    """Verify AudioRecorder tích hợp chunk state qua get_completed_chunks."""

    def test_get_completed_chunks_returns_list(self):
        from src.modules.audio_recorder import AudioRecorder

        rec = AudioRecorder()
        result = rec.get_completed_chunks()
        assert isinstance(result, list)
        assert result == []

    def test_chunk_path_format(self):
        from src.modules.audio_recorder import AudioRecorder

        rec = AudioRecorder()
        rec._output_path = "/tmp/meeting.wav"
        path = rec._chunk_path(0)
        assert path == "/tmp/meeting_chunk000.wav"
        path2 = rec._chunk_path(5)
        assert path2 == "/tmp/meeting_chunk005.wav"

    def test_start_resets_completed_chunks(self):
        from src.modules.audio_recorder import AudioRecorder

        rec = AudioRecorder()
        # Simulate pre-existing chunks from a previous session
        rec._completed_chunks = ["/tmp/old_chunk.wav"]

        # Patch the thread so start() doesn't actually try to record
        with patch.object(rec, "_record_loop"):
            import threading
            fake_thread = MagicMock(spec=threading.Thread)
            fake_thread.is_alive.return_value = True
            with patch("threading.Thread", return_value=fake_thread):
                rec.start(output_path="/tmp/test_output.wav")

        assert rec.get_completed_chunks() == []
