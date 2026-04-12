"""Tests cho analysis_service."""
from unittest.mock import MagicMock, patch

import pytest

import src.services.analysis_service as svc
from src.schema import MeetingAnalysis


def _make_mock_analysis() -> MeetingAnalysis:
    return MeetingAnalysis(epics=[], summary="Test summary")


class TestAnalysisService:
    def test_analyze_returns_meeting_analysis(self):
        mock_analyzer = MagicMock()
        mock_analyzer.return_value.analyze.return_value = _make_mock_analysis()

        with patch("src.services.analysis_service.OpenAIAnalyzer", mock_analyzer):
            result = svc.analyze("Transcript nội dung cuộc họp.")

        assert isinstance(result, MeetingAnalysis)
        assert result.summary == "Test summary"

    def test_analyze_passes_transcript(self):
        mock_analyzer = MagicMock()
        mock_analyzer.return_value.analyze.return_value = _make_mock_analysis()

        with patch("src.services.analysis_service.OpenAIAnalyzer", mock_analyzer):
            svc.analyze("my transcript")

        mock_analyzer.return_value.analyze.assert_called_once_with("my transcript")

    def test_analyze_raises_on_empty_transcript(self):
        with pytest.raises(ValueError, match="không được để trống"):
            svc.analyze("")

    def test_analyze_raises_on_whitespace_transcript(self):
        with pytest.raises(ValueError, match="không được để trống"):
            svc.analyze("   \n\t  ")
