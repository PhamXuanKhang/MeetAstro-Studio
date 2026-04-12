"""Tests cho LocalTranscriber — mock whisper.load_model."""
from unittest.mock import MagicMock, patch

import pytest

from src.providers.local_transcriber import LocalTranscriber


def _make_mock_whisper_model(result_text: str) -> MagicMock:
    mock_model = MagicMock()
    mock_model.transcribe.return_value = {"text": result_text}
    return mock_model


class TestLocalTranscriber:
    def test_transcribe_returns_text(self):
        mock_model = _make_mock_whisper_model("  văn bản transcript  ")
        transcriber = LocalTranscriber(model_name="base")

        with patch("whisper.load_model", return_value=mock_model):
            result = transcriber.transcribe("audio.mp3")

        assert result == "văn bản transcript"

    def test_load_model_lazy(self):
        """Model chỉ được load khi transcribe lần đầu."""
        transcriber = LocalTranscriber(model_name="base")
        assert transcriber._model is None

        mock_model = _make_mock_whisper_model("text")
        with patch("whisper.load_model", return_value=mock_model) as mock_load:
            transcriber.transcribe("audio.mp3")
            transcriber.transcribe("audio2.mp3")

        # load_model chỉ gọi 1 lần dù transcribe 2 lần
        assert mock_load.call_count == 1

    def test_transcribe_passes_language(self):
        mock_model = _make_mock_whisper_model("text")
        transcriber = LocalTranscriber(model_name="base")

        with patch("whisper.load_model", return_value=mock_model):
            transcriber.transcribe("audio.mp3", language="en")

        mock_model.transcribe.assert_called_once_with("audio.mp3", language="en")

    def test_transcribe_loads_correct_model(self):
        mock_model = _make_mock_whisper_model("text")
        transcriber = LocalTranscriber(model_name="small")

        with patch("whisper.load_model", return_value=mock_model) as mock_load:
            transcriber.transcribe("audio.mp3")

        mock_load.assert_called_once_with("small")

    def test_transcribe_handles_empty_result(self):
        mock_model = _make_mock_whisper_model("   ")
        transcriber = LocalTranscriber(model_name="base")

        with patch("whisper.load_model", return_value=mock_model):
            result = transcriber.transcribe("audio.mp3")

        assert result == ""
