"""Tests cho recording_service — mock AudioRecorder, verify wrapper."""
from unittest.mock import MagicMock, patch

import src.services.recording_service as svc


def _make_mock_recorder():
    mock = MagicMock()
    mock.is_recording = False
    mock.start.return_value = "/tmp/audio.wav"
    mock.stop.return_value = "/tmp/audio.wav"
    return mock


class TestRecordingService:
    def test_start_delegates_to_recorder(self):
        mock_rec = _make_mock_recorder()
        with patch("src.services.recording_service._recorder", mock_rec):
            path = svc.start_recording()
        assert path == "/tmp/audio.wav"
        mock_rec.start.assert_called_once()

    def test_stop_delegates_to_recorder(self):
        mock_rec = _make_mock_recorder()
        with patch("src.services.recording_service._recorder", mock_rec):
            path = svc.stop_recording()
        assert path == "/tmp/audio.wav"
        mock_rec.stop.assert_called_once()

    def test_is_recording_reflects_recorder_state(self):
        mock_rec = _make_mock_recorder()
        mock_rec.is_recording = True
        with patch("src.services.recording_service._recorder", mock_rec):
            assert svc.is_recording() is True
