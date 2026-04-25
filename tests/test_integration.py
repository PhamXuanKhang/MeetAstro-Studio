"""
Integration tests - P10: full pipeline + edge cases.
All external calls are mocked.
"""
from unittest.mock import MagicMock, patch

import pytest

from src.schema import Epic, MeetingAnalysis, Priority, Subtask, Task


def _make_analysis(
    summary: str = "Sprint planning meeting",
    n_epics: int = 1,
    confidence: float = 0.85,
) -> MeetingAnalysis:
    tasks = [
        Task(
            summary="Implement feature X",
            assignee="Alice",
            deadline="2025-01-31",
            priority=Priority.HIGH,
            confidence=confidence,
            subtasks=[
                Subtask(
                    summary="Write unit tests",
                    priority=Priority.MEDIUM,
                    confidence=confidence,
                )
            ],
        )
    ]
    epics = [Epic(summary=f"Epic {i+1}", tasks=tasks) for i in range(n_epics)]
    return MeetingAnalysis(
        epics=epics,
        summary=summary,
        key_decisions=["Use FastAPI", "Deploy to GCP"],
        parking_lot=["Review budget later"],
    )


SAMPLE_TRANSCRIPT = (
    "Alice: We need to implement feature X before January 31st.\n"
    "Bob: I'll assign it to the backend team.\n"
    "Alice: OK, this is critical priority."
)


class TestFullPipelineMock:
    """Mock all OpenAI calls, verify pipeline flow."""

    def test_transcribe_analyze_export_pipeline(self, tmp_path):
        """Transcribe -> Analyze -> Export markdown without raising exception."""
        from src.modules.exporter import export_markdown
        from src.services.transcription_service import transcribe
        from src.services.analysis_service import analyze

        audio_file = tmp_path / "meeting.wav"
        audio_file.write_bytes(b"\x00" * 100)

        mock_openai_t = MagicMock()
        mock_openai_t.return_value.transcribe.return_value = SAMPLE_TRANSCRIPT

        mock_analysis = _make_analysis()

        with patch("src.services.transcription_service.OpenAITranscriber", mock_openai_t):
            transcript = transcribe(str(audio_file))

        assert transcript == SAMPLE_TRANSCRIPT

        with patch("src.services.analysis_service.asyncio") as mock_asyncio:
            mock_asyncio.run.return_value = mock_analysis
            result = analyze(transcript)

        assert result.summary == "Sprint planning meeting"
        assert len(result.epics) == 1

        md = export_markdown(result)
        assert "Sprint planning meeting" in md
        assert "Implement feature X" in md


class TestEdgeCases:
    def test_empty_transcript_raises(self):
        """analyze() raises ValueError when transcript is empty."""
        from src.services.analysis_service import analyze

        with pytest.raises(ValueError, match="cannot be empty"):
            analyze("")

    def test_whitespace_transcript_raises(self):
        """analyze() raises ValueError when transcript is only whitespace."""
        from src.services.analysis_service import analyze

        with pytest.raises(ValueError, match="cannot be empty"):
            analyze("   \n\t  ")

    def test_no_api_key_uses_mock_analyzer(self):
        """When OPENAI_API_KEY is empty, analyze() returns MockAnalyzer result."""
        from src.services.analysis_service import analyze

        mock_settings = MagicMock()
        mock_settings.openai_api_key = ""
        with patch("src.services.analysis_service.get_settings", return_value=mock_settings):
            result = analyze(SAMPLE_TRANSCRIPT)

        assert isinstance(result, MeetingAnalysis)
        assert len(result.epics) >= 1

    def test_long_transcript_does_not_raise(self):
        """Long transcript (>14k tokens) does not raise exception when analyzing."""
        from src.services.analysis_service import analyze

        long_transcript = "Alice: Important content. " * 600
        mock_analysis = _make_analysis(summary="Long meeting")

        with patch("src.services.analysis_service.asyncio") as mock_asyncio:
            mock_asyncio.run.return_value = mock_analysis
            result = analyze(long_transcript)

        assert result.summary == "Long meeting"

    def test_missing_app_secret_key_raises_on_encrypt(self):
        """credential_vault.encrypt() raises ValueError when APP_SECRET_KEY is empty."""
        from src.modules.credential_vault import encrypt

        mock_settings = MagicMock()
        mock_settings.app_secret_key = ""
        with patch("src.modules.credential_vault.get_settings", return_value=mock_settings):
            with pytest.raises(ValueError, match="APP_SECRET_KEY"):
                encrypt("test-secret")

    def test_export_json_roundtrip(self):
        """Export JSON then parse back to MeetingAnalysis."""
        from src.modules.exporter import export_json

        analysis = _make_analysis()
        json_str = export_json(analysis)
        assert "Implement feature X" in json_str

        loaded = MeetingAnalysis.from_json(json_str)
        assert loaded.epics[0].tasks[0].summary == "Implement feature X"


class TestJiraStubMode:
    def test_stub_mode_when_no_credentials(self):
        """JiraClient uses stub when JIRA_BASE_URL is empty."""
        from src.modules.jira_client import JiraClient

        client = JiraClient(base_url="", email="", token="", project_key="")
        assert client.is_stub

    def test_push_to_jira_stub_result(self):
        """push_analysis_to_jira() returns is_stub=True when no credentials."""
        from src.modules.jira_client import JiraClient
        from src.services.jira_service import push_analysis_to_jira

        analysis = _make_analysis()
        stub_client = JiraClient(base_url="", email="", token="", project_key="")
        result = push_analysis_to_jira(analysis, client=stub_client)

        assert result.is_stub is True
        assert isinstance(result.epic_keys, list)

    def test_stub_create_epic_returns_stub_key(self):
        """JiraClient stub mode returns STUB-0 key."""
        from src.modules.jira_client import JiraClient
        from src.schema import Epic

        client = JiraClient(base_url="", email="", token="", project_key="")
        epic = Epic(summary="Test Epic")
        key = client.create_epic(epic)

        assert "STUB" in key.upper() or key.startswith("STUB")
