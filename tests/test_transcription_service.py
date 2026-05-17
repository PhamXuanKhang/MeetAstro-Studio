"""Tests for transcription_service (OpenAI Whisper API + WhisperLiveKit)."""
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
    """Test transcribe_diarized with the new 3-tier fallback:
    1. WhisperLiveKit (if WHISPER_LIVEKIT_URL set)
    2. OpenAI gpt-4o-transcribe-diarize
    3. Plain Whisper
    """

    def _mock_settings(self, whisper_livekit_url: str = "") -> MagicMock:
        """Return a mock settings object."""
        mock = MagicMock()
        mock.whisper_livekit_url = whisper_livekit_url
        mock.default_transcription_language = "en"
        return mock

    def test_uses_whisper_livekit_when_url_configured(self):
        """When WHISPER_LIVEKIT_URL is set, WhisperLiveKit should be used."""
        mock_wlk = MagicMock()
        mock_wlk.return_value.transcribe.return_value = "[Speaker 0]: livekit result"

        # Patch at the definition site — classes are imported inside the function
        with patch(
            "src.services.transcription_service.get_settings"
        ) as mock_settings_fn, patch(
            "src.providers.whisper_livekit_transcriber.WhisperLiveKitDiarizeTranscriber",
            mock_wlk,
        ):
            mock_settings_fn.return_value = self._mock_settings(
                whisper_livekit_url="wss://livekit.example.com/asr"
            )
            result = svc.transcribe_diarized("audio.mp3")

        assert result == "[Speaker 0]: livekit result"
        mock_wlk.return_value.transcribe.assert_called_once()

    def test_falls_back_to_openai_when_wlk_returns_empty(self):
        """When WhisperLiveKit returns empty text, falls back to OpenAI."""
        mock_wlk = MagicMock()
        mock_wlk.return_value.transcribe.return_value = ""  # empty

        mock_openai_diarize = MagicMock()
        mock_openai_diarize.return_value.transcribe.return_value = "[Speaker 0]: openai result"

        with patch(
            "src.services.transcription_service.get_settings"
        ) as mock_settings_fn, patch(
            "src.providers.whisper_livekit_transcriber.WhisperLiveKitDiarizeTranscriber",
            mock_wlk,
        ), patch(
            "src.providers.openai_diarize_transcriber.OpenAIDiarizeTranscriber",
            mock_openai_diarize,
        ):
            mock_settings_fn.return_value = self._mock_settings(
                whisper_livekit_url="wss://livekit.example.com/asr"
            )
            result = svc.transcribe_diarized("audio.mp3")

        assert result == "[Speaker 0]: openai result"

    def test_falls_back_to_openai_when_wlk_raises(self):
        """When WhisperLiveKit raises, falls back to OpenAI."""
        mock_wlk = MagicMock()
        mock_wlk.return_value.transcribe.side_effect = RuntimeError("WLK down")

        mock_openai_diarize = MagicMock()
        mock_openai_diarize.return_value.transcribe.return_value = "[Speaker 0]: openai result"

        with patch(
            "src.services.transcription_service.get_settings"
        ) as mock_settings_fn, patch(
            "src.providers.whisper_livekit_transcriber.WhisperLiveKitDiarizeTranscriber",
            mock_wlk,
        ), patch(
            "src.providers.openai_diarize_transcriber.OpenAIDiarizeTranscriber",
            mock_openai_diarize,
        ):
            mock_settings_fn.return_value = self._mock_settings(
                whisper_livekit_url="wss://livekit.example.com/asr"
            )
            result = svc.transcribe_diarized("audio.mp3")

        assert result == "[Speaker 0]: openai result"

    def test_uses_openai_when_wlk_url_not_set(self):
        """When WHISPER_LIVEKIT_URL is empty, uses OpenAI directly."""
        mock_openai_diarize = MagicMock()
        mock_openai_diarize.return_value.transcribe.return_value = "[Speaker 0]: openai result"

        with patch(
            "src.services.transcription_service.get_settings"
        ) as mock_settings_fn, patch(
            "src.providers.openai_diarize_transcriber.OpenAIDiarizeTranscriber",
            mock_openai_diarize,
        ):
            mock_settings_fn.return_value = self._mock_settings(whisper_livekit_url="")
            result = svc.transcribe_diarized("audio.mp3")

        assert result == "[Speaker 0]: openai result"
        mock_openai_diarize.return_value.transcribe.assert_called_once()

    def test_fallback_to_plain_transcribe_on_diarize_failure(self):
        """When diarization fails, falls back to plain Whisper."""
        mock_openai_diarize = MagicMock()
        mock_openai_diarize.return_value.transcribe.side_effect = RuntimeError("API fail")

        mock_plain = MagicMock()
        mock_plain.return_value.transcribe.return_value = "plain fallback"

        with patch(
            "src.services.transcription_service.get_settings"
        ) as mock_settings_fn, patch(
            "src.providers.openai_diarize_transcriber.OpenAIDiarizeTranscriber",
            mock_openai_diarize,
        ), patch(
            "src.services.transcription_service.OpenAITranscriber",
            mock_plain,
        ):
            mock_settings_fn.return_value = self._mock_settings(whisper_livekit_url="")
            result = svc.transcribe_diarized("audio.mp3")

        assert result == "plain fallback"

    def test_fallback_logs_warning(self, caplog):
        """Fallback to plain Whisper logs a warning."""
        mock_openai_diarize = MagicMock()
        mock_openai_diarize.return_value.transcribe.side_effect = RuntimeError("API fail")

        mock_plain = MagicMock()
        mock_plain.return_value.transcribe.return_value = "fallback"

        with patch(
            "src.services.transcription_service.get_settings"
        ) as mock_settings_fn, patch(
            "src.providers.openai_diarize_transcriber.OpenAIDiarizeTranscriber",
            mock_openai_diarize,
        ), patch(
            "src.services.transcription_service.OpenAITranscriber",
            mock_plain,
        ):
            mock_settings_fn.return_value = self._mock_settings(whisper_livekit_url="")
            with caplog.at_level(logging.WARNING, logger="src.services.transcription_service"):
                svc.transcribe_diarized("audio.mp3")

        assert any("falling back" in r.message.lower() for r in caplog.records)

    def test_language_passed_through_to_wlk(self):
        """Language is passed to WhisperLiveKit when configured."""
        mock_wlk = MagicMock()
        mock_wlk.return_value.transcribe.return_value = "[Speaker 0]: text"

        with patch(
            "src.services.transcription_service.get_settings"
        ) as mock_settings_fn, patch(
            "src.providers.whisper_livekit_transcriber.WhisperLiveKitDiarizeTranscriber",
            mock_wlk,
        ):
            mock_settings_fn.return_value = self._mock_settings(
                whisper_livekit_url="wss://livekit.example.com/asr"
            )
            svc.transcribe_diarized("audio.mp3", language="vi")

        mock_wlk.return_value.transcribe.assert_called_once_with("audio.mp3", language="vi")
