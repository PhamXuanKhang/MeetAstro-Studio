"""Tests cho OpenAIAnalyzer — mock OpenAI client."""
import json
from unittest.mock import MagicMock, patch

import pytest

from src.providers.openai_analyzer import OpenAIAnalyzer
from src.schema import MeetingAnalysis, Priority


SAMPLE_JSON = {
    "summary": "Cuộc họp về launch Q1.",
    "epics": [
        {
            "summary": "Ra mắt sản phẩm",
            "description": "Chuẩn bị launch Q1.",
            "tasks": [
                {
                    "summary": "Triển khai hệ thống",
                    "assignee": "Nam",
                    "deadline": "2024-01-15",
                    "priority": "High",
                    "context": "Cần triển khai trước Tết.",
                    "subtasks": [],
                }
            ],
        }
    ],
}


def _make_mock_client(content: str) -> MagicMock:
    """Tạo mock OpenAI client trả về content JSON."""
    mock_choice = MagicMock()
    mock_choice.message.content = content
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


class TestOpenAIAnalyzer:
    def test_analyze_returns_meeting_analysis(self):
        mock_client = _make_mock_client(json.dumps(SAMPLE_JSON))
        analyzer = OpenAIAnalyzer.__new__(OpenAIAnalyzer)
        analyzer._client = mock_client
        analyzer._model = "gpt-4o"
        analyzer._system_prompt = "system"

        result = analyzer.analyze("transcript text")

        assert isinstance(result, MeetingAnalysis)
        assert result.summary == "Cuộc họp về launch Q1."
        assert len(result.epics) == 1
        assert result.epics[0].tasks[0].priority == Priority.HIGH

    def test_analyze_passes_transcript_to_api(self):
        mock_client = _make_mock_client(json.dumps(SAMPLE_JSON))
        analyzer = OpenAIAnalyzer.__new__(OpenAIAnalyzer)
        analyzer._client = mock_client
        analyzer._model = "gpt-4o"
        analyzer._system_prompt = "system"

        analyzer.analyze("my transcript")

        call_kwargs = mock_client.chat.completions.create.call_args
        messages = call_kwargs.kwargs["messages"]
        user_msg = next(m for m in messages if m["role"] == "user")
        assert user_msg["content"] == "my transcript"

    def test_analyze_uses_json_mode(self):
        mock_client = _make_mock_client(json.dumps(SAMPLE_JSON))
        analyzer = OpenAIAnalyzer.__new__(OpenAIAnalyzer)
        analyzer._client = mock_client
        analyzer._model = "gpt-4o"
        analyzer._system_prompt = "system"

        analyzer.analyze("transcript")

        call_kwargs = mock_client.chat.completions.create.call_args
        assert call_kwargs.kwargs["response_format"] == {"type": "json_object"}

    def test_analyze_raises_on_invalid_json(self):
        mock_client = _make_mock_client("not valid json {{")
        analyzer = OpenAIAnalyzer.__new__(OpenAIAnalyzer)
        analyzer._client = mock_client
        analyzer._model = "gpt-4o"
        analyzer._system_prompt = "system"

        with pytest.raises(ValueError, match="Không parse được"):
            analyzer.analyze("transcript")

    def test_analyze_retries_on_api_error(self):
        import openai

        mock_choice = MagicMock()
        mock_choice.message.content = json.dumps(SAMPLE_JSON)
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = [
            openai.APIConnectionError(request=MagicMock()),
            mock_response,
        ]

        analyzer = OpenAIAnalyzer.__new__(OpenAIAnalyzer)
        analyzer._client = mock_client
        analyzer._model = "gpt-4o"
        analyzer._system_prompt = "system"

        with patch("src.providers.openai_analyzer.time.sleep"):
            result = analyzer.analyze("transcript")

        assert isinstance(result, MeetingAnalysis)
        assert mock_client.chat.completions.create.call_count == 2

    def test_analyze_raises_after_max_retries(self):
        import openai

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = openai.APIConnectionError(
            request=MagicMock()
        )

        analyzer = OpenAIAnalyzer.__new__(OpenAIAnalyzer)
        analyzer._client = mock_client
        analyzer._model = "gpt-4o"
        analyzer._system_prompt = "system"

        with patch("src.providers.openai_analyzer.time.sleep"):
            with pytest.raises(RuntimeError, match="thất bại sau"):
                analyzer.analyze("transcript")

        assert mock_client.chat.completions.create.call_count == 3
