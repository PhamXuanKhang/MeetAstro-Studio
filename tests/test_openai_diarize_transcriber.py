"""Tests cho OpenAIDiarizeTranscriber — mock OpenAI client."""
from unittest.mock import MagicMock, mock_open, patch

import pytest

from src.providers.openai_diarize_transcriber import (
    DiarizedSegment,
    OpenAIDiarizeTranscriber,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_segment(speaker: str, start: float, end: float, text: str) -> object:
    """Tạo mock segment object giống response của OpenAI API."""
    seg = MagicMock()
    seg.speaker = speaker
    seg.start = start
    seg.end = end
    seg.text = text
    return seg


def _make_transcriber(segments: list) -> tuple[OpenAIDiarizeTranscriber, MagicMock]:
    """Tạo transcriber với mock client."""
    mock_response = MagicMock()
    mock_response.utterances = segments
    mock_response.segments = None

    mock_client = MagicMock()
    mock_client.audio.transcriptions.create.return_value = mock_response

    transcriber = OpenAIDiarizeTranscriber.__new__(OpenAIDiarizeTranscriber)
    transcriber._client = mock_client
    return transcriber, mock_client


# ── Tests: transcribe_to_segments ─────────────────────────────────────────────

class TestTranscribeToSegments:
    def test_returns_correct_segments(self):
        segs = [
            _make_segment("Speaker 0", 0.0, 5.0, "Hôm nay chúng ta họp"),
            _make_segment("Speaker 1", 5.5, 10.0, "Vâng tôi đồng ý"),
        ]
        transcriber, _ = _make_transcriber(segs)

        with patch("builtins.open", mock_open(read_data=b"audio")):
            result = transcriber.transcribe_to_segments("audio.mp3")

        assert len(result) == 2
        assert result[0]["speaker"] == "Speaker 0"
        assert result[0]["start"] == 0.0
        assert result[0]["end"] == 5.0
        assert result[0]["text"] == "Hôm nay chúng ta họp"
        assert result[1]["speaker"] == "Speaker 1"

    def test_chunking_strategy_always_auto(self):
        transcriber, mock_client = _make_transcriber([])
        with patch("builtins.open", mock_open(read_data=b"audio")):
            transcriber.transcribe_to_segments("audio.mp3")

        call_kwargs = mock_client.audio.transcriptions.create.call_args
        assert call_kwargs.kwargs.get("chunking_strategy") == "auto"

    def test_model_is_correct(self):
        transcriber, mock_client = _make_transcriber([])
        with patch("builtins.open", mock_open(read_data=b"audio")):
            transcriber.transcribe_to_segments("audio.mp3")

        call_kwargs = mock_client.audio.transcriptions.create.call_args
        assert call_kwargs.kwargs.get("model") == "gpt-4o-transcribe-diarize"

    def test_response_format_is_diarized_json(self):
        transcriber, mock_client = _make_transcriber([])
        with patch("builtins.open", mock_open(read_data=b"audio")):
            transcriber.transcribe_to_segments("audio.mp3")

        call_kwargs = mock_client.audio.transcriptions.create.call_args
        assert call_kwargs.kwargs.get("response_format") == "diarized_json"

    def test_empty_segments_response(self):
        transcriber, _ = _make_transcriber([])
        with patch("builtins.open", mock_open(read_data=b"audio")):
            result = transcriber.transcribe_to_segments("audio.mp3")
        assert result == []

    def test_skips_empty_text_segments(self):
        segs = [
            _make_segment("Speaker 0", 0.0, 1.0, ""),  # rỗng — nên bị bỏ qua
            _make_segment("Speaker 0", 1.0, 5.0, "Nội dung thật"),
        ]
        transcriber, _ = _make_transcriber(segs)
        with patch("builtins.open", mock_open(read_data=b"audio")):
            result = transcriber.transcribe_to_segments("audio.mp3")
        assert len(result) == 1
        assert result[0]["text"] == "Nội dung thật"

    def test_raises_file_not_found(self):
        transcriber, _ = _make_transcriber([])
        with pytest.raises(FileNotFoundError, match="Audio file not found"):
            transcriber.transcribe_to_segments("/nonexistent/audio.mp3")

    def test_raises_immediately_on_api_error(self):
        import openai

        mock_client = MagicMock()
        mock_client.audio.transcriptions.create.side_effect = openai.APIConnectionError(
            request=MagicMock()
        )
        transcriber = OpenAIDiarizeTranscriber.__new__(OpenAIDiarizeTranscriber)
        transcriber._client = mock_client

        with patch("builtins.open", mock_open(read_data=b"audio")):
            with patch("src.providers.openai_diarize_transcriber.time.sleep"):
                with pytest.raises(RuntimeError, match="failed after"):
                    transcriber.transcribe_to_segments("audio.mp3")

        assert mock_client.audio.transcriptions.create.call_count == 1


# ── Tests: transcribe (string output) ─────────────────────────────────────────

class TestTranscribe:
    def test_transcribe_returns_labeled_string(self):
        segs = [
            _make_segment("Speaker 0", 0.0, 5.0, "Hôm nay chúng ta họp"),
            _make_segment("Speaker 1", 5.5, 10.0, "Vâng tôi đồng ý"),
        ]
        transcriber, _ = _make_transcriber(segs)

        with patch("builtins.open", mock_open(read_data=b"audio")):
            result = transcriber.transcribe("audio.mp3")

        assert "[Speaker 0]: Hôm nay chúng ta họp" in result
        assert "[Speaker 1]: Vâng tôi đồng ý" in result

    def test_adjacent_same_speaker_merged(self):
        segs = [
            _make_segment("Speaker 0", 0.0, 2.0, "Phần một"),
            _make_segment("Speaker 0", 2.5, 5.0, "phần hai"),
            _make_segment("Speaker 1", 5.5, 8.0, "Tôi nghe"),
        ]
        transcriber, _ = _make_transcriber(segs)

        with patch("builtins.open", mock_open(read_data=b"audio")):
            result = transcriber.transcribe("audio.mp3")

        lines = result.split("\n")
        assert len(lines) == 2  # 2 speakers sau khi merge
        assert "Phần một phần hai" in lines[0]

    def test_empty_segments_returns_empty_string(self):
        transcriber, _ = _make_transcriber([])
        with patch("builtins.open", mock_open(read_data=b"audio")):
            result = transcriber.transcribe("audio.mp3")
        assert result == ""

    def test_single_speaker(self):
        segs = [_make_segment("Speaker 0", 0.0, 10.0, "Toàn bộ nội dung")]
        transcriber, _ = _make_transcriber(segs)

        with patch("builtins.open", mock_open(read_data=b"audio")):
            result = transcriber.transcribe("audio.mp3")

        assert result == "[Speaker 0]: Toàn bộ nội dung"


# ── Tests: _segments_to_string (unit) ─────────────────────────────────────────

class TestSegmentsToString:
    def test_basic_two_speakers(self):
        segments: list[DiarizedSegment] = [
            {"speaker": "Speaker 0", "start": 0.0, "end": 5.0, "text": "Câu A"},
            {"speaker": "Speaker 1", "start": 5.5, "end": 10.0, "text": "Câu B"},
        ]
        result = OpenAIDiarizeTranscriber._segments_to_string(segments)
        assert result == "[Speaker 0]: Câu A\n[Speaker 1]: Câu B"

    def test_empty_list(self):
        assert OpenAIDiarizeTranscriber._segments_to_string([]) == ""

    def test_alternating_speakers(self):
        segments: list[DiarizedSegment] = [
            {"speaker": "A", "start": 0.0, "end": 1.0, "text": "Xin chào"},
            {"speaker": "B", "start": 1.5, "end": 2.0, "text": "Chào bạn"},
            {"speaker": "A", "start": 2.5, "end": 3.0, "text": "Hẹn gặp lại"},
        ]
        result = OpenAIDiarizeTranscriber._segments_to_string(segments)
        lines = result.split("\n")
        assert len(lines) == 3
