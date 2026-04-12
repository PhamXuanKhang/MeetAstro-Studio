"""Tests cho OpenAITranscriber — mock OpenAI client."""
import io
from unittest.mock import MagicMock, mock_open, patch

import pytest

from src.providers.openai_transcriber import OpenAITranscriber


def _make_transcriber(response_text: str) -> tuple[OpenAITranscriber, MagicMock]:
    mock_response = MagicMock()
    mock_response.text = response_text
    mock_client = MagicMock()
    mock_client.audio.transcriptions.create.return_value = mock_response

    transcriber = OpenAITranscriber.__new__(OpenAITranscriber)
    transcriber._client = mock_client
    return transcriber, mock_client


class TestOpenAITranscriber:
    def test_transcribe_returns_text(self):
        transcriber, _ = _make_transcriber("  xin chào thế giới  ")
        with patch("builtins.open", mock_open(read_data=b"audio")):
            result = transcriber.transcribe("audio.mp3")
        assert result == "xin chào thế giới"

    def test_transcribe_calls_whisper_model(self):
        transcriber, mock_client = _make_transcriber("text")
        with patch("builtins.open", mock_open(read_data=b"audio")):
            transcriber.transcribe("audio.mp3", language="vi")
        call_kwargs = mock_client.audio.transcriptions.create.call_args
        assert call_kwargs.kwargs["model"] == "whisper-1"
        assert call_kwargs.kwargs["language"] == "vi"

    def test_transcribe_raises_file_not_found(self):
        transcriber, _ = _make_transcriber("text")
        with pytest.raises(FileNotFoundError, match="Không tìm thấy file audio"):
            transcriber.transcribe("/nonexistent/path.mp3")

    def test_transcribe_retries_on_api_error(self):
        import openai

        mock_response = MagicMock()
        mock_response.text = "hello"
        mock_client = MagicMock()
        mock_client.audio.transcriptions.create.side_effect = [
            openai.APIConnectionError(request=MagicMock()),
            mock_response,
        ]
        transcriber = OpenAITranscriber.__new__(OpenAITranscriber)
        transcriber._client = mock_client

        with patch("builtins.open", mock_open(read_data=b"audio")):
            with patch("src.providers.openai_transcriber.time.sleep"):
                result = transcriber.transcribe("audio.mp3")

        assert result == "hello"
        assert mock_client.audio.transcriptions.create.call_count == 2

    def test_transcribe_raises_after_max_retries(self):
        import openai

        mock_client = MagicMock()
        mock_client.audio.transcriptions.create.side_effect = openai.APIConnectionError(
            request=MagicMock()
        )
        transcriber = OpenAITranscriber.__new__(OpenAITranscriber)
        transcriber._client = mock_client

        with patch("builtins.open", mock_open(read_data=b"audio")):
            with patch("src.providers.openai_transcriber.time.sleep"):
                with pytest.raises(RuntimeError, match="thất bại sau"):
                    transcriber.transcribe("audio.mp3")

        assert mock_client.audio.transcriptions.create.call_count == 3
