"""Tests for transcription_service (OpenAI Whisper API only)."""
import logging
from unittest.mock import MagicMock, patch

import pytest

import src.services.transcription_service as svc


class TestTranscriptionService:
    def test_uses_openai_transcriber(self):
        mock_openai = MagicMock()
        mock_openai.return_value.transcribe.return_value = "openai transcript"

        with patch("src.services.transcription_service.OpenAITranscriber", mock_openai):
            result = svc.transcribe("audio.mp3")

        assert result == "openai transcript"
        mock_openai.return_value.transcribe.assert_called_once()

    def test_raises_on_openai_failure(self):
        mock_openai = MagicMock()
        mock_openai.return_value.transcribe.side_effect = RuntimeError("API down")

        with patch("src.services.transcription_service.OpenAITranscriber", mock_openai):
            with pytest.raises(RuntimeError, match="Whisper API failed"):
                svc.transcribe("audio.mp3")

    def test_language_passed_through(self):
        mock_openai = MagicMock()
        mock_openai.return_value.transcribe.return_value = "transcript"

        with patch("src.services.transcription_service.OpenAITranscriber", mock_openai):
            svc.transcribe("audio.mp3", language="en")

        mock_openai.return_value.transcribe.assert_called_once_with("audio.mp3", language="en")


class TestTranscribeDiarized:
    def test_returns_diarized_transcript_on_success(self):
        mock_diarize = MagicMock()
        mock_diarize.return_value.transcribe.return_value = (
            "[Speaker 0]: Meeting today\n[Speaker 1]: Yes I agree"
        )

        with patch("src.services.transcription_service.OpenAIDiarizeTranscriber", mock_diarize):
            result = svc.transcribe_diarized("audio.mp3")

        assert "[Speaker 0]:" in result
        assert "[Speaker 1]:" in result

    def test_fallback_to_plain_transcribe_on_failure(self):
        mock_diarize = MagicMock()
        mock_diarize.return_value.transcribe.side_effect = RuntimeError("API fail")

        mock_openai = MagicMock()
        mock_openai.return_value.transcribe.return_value = "plain transcript fallback"

        with patch("src.services.transcription_service.OpenAIDiarizeTranscriber", mock_diarize):
            with patch("src.services.transcription_service.OpenAITranscriber", mock_openai):
                result = svc.transcribe_diarized("audio.mp3")

        assert result == "plain transcript fallback"

    def test_fallback_logs_warning(self, caplog):
        mock_diarize = MagicMock()
        mock_diarize.return_value.transcribe.side_effect = RuntimeError("API fail")

        mock_openai = MagicMock()
        mock_openai.return_value.transcribe.return_value = "fallback"

        with patch("src.services.transcription_service.OpenAIDiarizeTranscriber", mock_diarize):
            with patch("src.services.transcription_service.OpenAITranscriber", mock_openai):
                with caplog.at_level(logging.WARNING, logger="src.services.transcription_service"):
                    svc.transcribe_diarized("audio.mp3")

        assert any("falling back" in r.message.lower() for r in caplog.records)

    def test_language_passed_through(self):
        mock_diarize = MagicMock()
        mock_diarize.return_value.transcribe.return_value = "[Speaker 0]: text"

        with patch("src.services.transcription_service.OpenAIDiarizeTranscriber", mock_diarize):
            svc.transcribe_diarized("audio.mp3", language="en")

        mock_diarize.return_value.transcribe.assert_called_once_with("audio.mp3", language="en")
