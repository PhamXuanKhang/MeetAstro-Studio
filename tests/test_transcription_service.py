"""Tests cho transcription_service — đặc biệt test fallback chain."""
import logging
from unittest.mock import MagicMock, patch

import pytest

import src.services.transcription_service as svc


class TestTranscriptionService:
    def test_uses_openai_transcriber_first(self):
        mock_openai = MagicMock()
        mock_openai.return_value.transcribe.return_value = "openai transcript"

        with patch("src.services.transcription_service.OpenAITranscriber", mock_openai):
            result = svc.transcribe("audio.mp3")

        assert result == "openai transcript"
        mock_openai.return_value.transcribe.assert_called_once_with("audio.mp3", language="vi")

    def test_fallback_to_local_on_openai_failure(self):
        mock_openai = MagicMock()
        mock_openai.return_value.transcribe.side_effect = RuntimeError("API down")

        mock_local = MagicMock()
        mock_local.return_value.transcribe.return_value = "local transcript"

        with patch("src.services.transcription_service.OpenAITranscriber", mock_openai):
            with patch("src.services.transcription_service.LocalTranscriber", mock_local):
                result = svc.transcribe("audio.mp3")

        assert result == "local transcript"

    def test_fallback_logs_warning(self, caplog):
        mock_openai = MagicMock()
        mock_openai.return_value.transcribe.side_effect = RuntimeError("API down")

        mock_local = MagicMock()
        mock_local.return_value.transcribe.return_value = "local transcript"

        with patch("src.services.transcription_service.OpenAITranscriber", mock_openai):
            with patch("src.services.transcription_service.LocalTranscriber", mock_local):
                with caplog.at_level(logging.WARNING, logger="src.services.transcription_service"):
                    svc.transcribe("audio.mp3")

        assert any("fallback" in r.message.lower() or "local" in r.message.lower()
                   for r in caplog.records)

    def test_raises_when_both_fail(self):
        mock_openai = MagicMock()
        mock_openai.return_value.transcribe.side_effect = RuntimeError("OpenAI fail")

        mock_local = MagicMock()
        mock_local.return_value.transcribe.side_effect = RuntimeError("Local fail")

        with patch("src.services.transcription_service.OpenAITranscriber", mock_openai):
            with patch("src.services.transcription_service.LocalTranscriber", mock_local):
                with pytest.raises(RuntimeError, match="đều thất bại"):
                    svc.transcribe("audio.mp3")

    def test_language_passed_through(self):
        mock_openai = MagicMock()
        mock_openai.return_value.transcribe.return_value = "transcript"

        with patch("src.services.transcription_service.OpenAITranscriber", mock_openai):
            svc.transcribe("audio.mp3", language="en")

        mock_openai.return_value.transcribe.assert_called_once_with("audio.mp3", language="en")
