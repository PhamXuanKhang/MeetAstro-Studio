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


class TestTranscribeChunks:
    def _patch_transcribe(self, return_value="ok"):
        return patch("src.services.transcription_service.transcribe", return_value=return_value)

    def test_empty_paths_returns_empty_string(self):
        assert svc.transcribe_chunks([]) == ""

    def test_single_chunk_returns_transcript(self):
        with self._patch_transcribe("Hello world"):
            result = svc.transcribe_chunks(["/tmp/chunk000.wav"])
        assert result == "Hello world"

    def test_multiple_chunks_concatenated(self):
        texts = ["Hello", "world", "foo"]
        call_count = iter(texts)
        with patch("src.services.transcription_service.transcribe", side_effect=texts):
            result = svc.transcribe_chunks(["/tmp/c0.wav", "/tmp/c1.wav", "/tmp/c2.wav"])
        assert result == "Hello world foo"

    def test_failed_chunk_is_skipped(self):
        def _side_effect(path, language="vi"):
            if "bad" in path:
                raise RuntimeError("bad chunk")
            return "good"

        with patch("src.services.transcription_service.transcribe", side_effect=_side_effect):
            result = svc.transcribe_chunks(["/tmp/good.wav", "/tmp/bad.wav"])
        assert result == "good"

    def test_large_file_uses_local_transcriber(self, tmp_path):
        big_file = tmp_path / "big.wav"
        big_file.write_bytes(b"x" * (26 * 1024 * 1024))  # 26 MB > 25 MB limit

        mock_local = MagicMock()
        mock_local.return_value.transcribe.return_value = "local result"

        with patch("src.services.transcription_service.LocalTranscriber", mock_local):
            result = svc.transcribe_chunks([str(big_file)])

        mock_local.return_value.transcribe.assert_called_once()
        assert result == "local result"


class TestTranscribeDiarized:
    """Tests cho transcribe_diarized() — success + fallback."""

    def test_returns_diarized_transcript_on_success(self):
        mock_diarize = MagicMock()
        mock_diarize.return_value.transcribe.return_value = (
            "[Speaker 0]: Hôm nay họp\n[Speaker 1]: Vâng đồng ý"
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
        import logging

        mock_diarize = MagicMock()
        mock_diarize.return_value.transcribe.side_effect = RuntimeError("API fail")

        mock_openai = MagicMock()
        mock_openai.return_value.transcribe.return_value = "fallback"

        with patch("src.services.transcription_service.OpenAIDiarizeTranscriber", mock_diarize):
            with patch("src.services.transcription_service.OpenAITranscriber", mock_openai):
                with caplog.at_level(logging.WARNING, logger="src.services.transcription_service"):
                    svc.transcribe_diarized("audio.mp3")

        assert any("fallback" in r.message.lower() for r in caplog.records)

    def test_language_passed_through(self):
        mock_diarize = MagicMock()
        mock_diarize.return_value.transcribe.return_value = "[Speaker 0]: text"

        with patch("src.services.transcription_service.OpenAIDiarizeTranscriber", mock_diarize):
            svc.transcribe_diarized("audio.mp3", language="en")

        mock_diarize.return_value.transcribe.assert_called_once_with("audio.mp3", language="en")
