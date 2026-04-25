"""Tests for analysis_service."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import src.services.analysis_service as svc
from src.schema import MeetingAnalysis


def _make_mock_analysis() -> MeetingAnalysis:
    return MeetingAnalysis(epics=[], summary="Test summary")


_MOCK_SUMMARY = {
    "summary": "Test summary",
    "key_decisions": [],
    "discussion_points": [],
    "parking_lot_items": [],
}

_MOCK_AI_ITEMS: list = []


_SVC = "src.services.analysis_service"


class TestAnalysisService:
    def test_analyze_returns_meeting_analysis(self):
        mock_summary = AsyncMock(return_value=_MOCK_SUMMARY)
        with (
            patch(f"{_SVC}.generate_summary", new=mock_summary),
            patch(f"{_SVC}._extract_via_openai", return_value=_MOCK_AI_ITEMS),
        ):
            result = svc.analyze("Transcript content of the meeting.")

        assert isinstance(result, MeetingAnalysis)
        assert result.summary == "Test summary"

    def test_analyze_passes_transcript(self):
        mock_extract = MagicMock(return_value=_MOCK_AI_ITEMS)
        mock_summary = AsyncMock(return_value=_MOCK_SUMMARY)
        with (
            patch(f"{_SVC}.generate_summary", new=mock_summary),
            patch(f"{_SVC}._extract_via_openai", mock_extract),
        ):
            svc.analyze("my transcript")

        mock_extract.assert_called_once_with("my transcript")

    def test_analyze_raises_on_empty_transcript(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            svc.analyze("")

    def test_analyze_raises_on_whitespace_transcript(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            svc.analyze("   \n\t  ")

    def test_analyze_uses_mock_analyzer_when_no_api_key(self):
        mock_settings = MagicMock()
        mock_settings.openai_api_key = ""
        with patch(f"{_SVC}.get_settings", return_value=mock_settings):
            result = svc.analyze("transcript")
        assert isinstance(result, MeetingAnalysis)
        assert "[MOCK]" in result.summary
