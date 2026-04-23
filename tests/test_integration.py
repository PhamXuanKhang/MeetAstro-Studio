"""
Integration tests — P10: full pipeline + edge cases.
Tất cả external calls đều được mock.
"""
from unittest.mock import MagicMock, patch

import pytest

from src.schema import Epic, MeetingAnalysis, Priority, Subtask, Task


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_analysis(
    summary: str = "Họp sprint planning",
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
        key_decisions=["Dùng FastAPI", "Deploy lên GCP"],
        parking_lot=["Review budget sau"],
    )


SAMPLE_TRANSCRIPT = (
    "Alice: Chúng ta cần implement feature X trước ngày 31/01.\n"
    "Bob: Tôi sẽ assign cho team backend.\n"
    "Alice: OK, đây là critical priority."
)


# ══════════════════════════════════════════════════════════════════════════════
# Test: Full pipeline mock (transcribe → analyze → export)
# ══════════════════════════════════════════════════════════════════════════════

class TestFullPipelineMock:
    """Mock toàn bộ OpenAI calls, verify pipeline flow."""

    def test_transcribe_analyze_export_pipeline(self, tmp_path):
        """Transcribe → Analyze → Export markdown không raise exception."""
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

        assert result.summary == "Họp sprint planning"
        assert len(result.epics) == 1

        md = export_markdown(result)
        assert "Họp sprint planning" in md
        assert "Implement feature X" in md



# ══════════════════════════════════════════════════════════════════════════════
# Test: Edge cases
# ══════════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    def test_empty_transcript_raises(self):
        """analyze() raise ValueError khi transcript rỗng."""
        from src.services.analysis_service import analyze

        with pytest.raises(ValueError, match="trống"):
            analyze("")

    def test_whitespace_transcript_raises(self):
        """analyze() raise ValueError khi transcript chỉ có khoảng trắng."""
        from src.services.analysis_service import analyze

        with pytest.raises(ValueError, match="trống"):
            analyze("   \n\t  ")

    def test_no_api_key_uses_mock_analyzer(self):
        """Khi OPENAI_API_KEY rỗng, analyze() trả về MockAnalyzer result."""
        from src.services.analysis_service import analyze

        with patch("src.services.analysis_service.OPENAI_API_KEY", ""):
            result = analyze(SAMPLE_TRANSCRIPT)

        assert isinstance(result, MeetingAnalysis)
        assert len(result.epics) >= 1

    def test_long_transcript_does_not_raise(self):
        """Transcript dài (>14k tokens) không raise ngoại lệ khi analyze."""
        from src.services.analysis_service import analyze

        long_transcript = "Alice: Nội dung quan trọng. " * 600  # ~14k+ words
        mock_analysis = _make_analysis(summary="Long meeting")

        with patch("src.services.analysis_service.asyncio") as mock_asyncio:
            mock_asyncio.run.return_value = mock_analysis
            result = analyze(long_transcript)

        assert result.summary == "Long meeting"

    def test_missing_app_secret_key_raises_on_encrypt(self):
        """credential_vault.encrypt() raise ValueError khi APP_SECRET_KEY rỗng."""
        from src.modules.credential_vault import encrypt

        with patch("src.modules.credential_vault.APP_SECRET_KEY", ""):
            with pytest.raises(ValueError, match="APP_SECRET_KEY"):
                encrypt("test-secret")

    def test_transcribe_chunks_empty_returns_empty_string(self):
        """transcribe_chunks([]) trả về empty string."""
        from src.services.transcription_service import transcribe_chunks

        assert transcribe_chunks([]) == ""

    def test_export_json_roundtrip(self):
        """Export JSON rồi parse lại được MeetingAnalysis."""
        from src.modules.exporter import export_json

        analysis = _make_analysis()
        json_str = export_json(analysis)
        assert "Implement feature X" in json_str

        loaded = MeetingAnalysis.from_json(json_str)
        assert loaded.epics[0].tasks[0].summary == "Implement feature X"


# ══════════════════════════════════════════════════════════════════════════════
# Test: Jira stub mode
# ══════════════════════════════════════════════════════════════════════════════

class TestJiraStubMode:
    def test_stub_mode_when_no_credentials(self):
        """JiraClient dùng stub khi JIRA_BASE_URL rỗng."""
        from src.modules.jira_client import JiraClient

        with patch("src.modules.jira_client.JIRA_BASE_URL", ""):
            client = JiraClient()
            assert client.is_stub

    def test_push_to_jira_stub_result(self):
        """push_analysis_to_jira() trả về is_stub=True khi không có credentials."""
        from src.services.jira_service import push_analysis_to_jira

        analysis = _make_analysis()

        with patch("src.modules.jira_client.JIRA_BASE_URL", ""):
            with patch("src.modules.jira_client.JIRA_API_TOKEN", ""):
                result = push_analysis_to_jira(analysis)

        assert result.is_stub is True
        assert isinstance(result.epic_keys, list)

    def test_stub_create_epic_returns_stub_key(self):
        """JiraClient stub mode trả về STUB-0 key."""
        from src.modules.jira_client import JiraClient
        from src.schema import Epic

        with patch("src.modules.jira_client.JIRA_BASE_URL", ""):
            client = JiraClient()
            epic = Epic(summary="Test Epic")
            key = client.create_epic(epic)

        assert "STUB" in key.upper() or key.startswith("STUB")


# ══════════════════════════════════════════════════════════════════════════════
# Test: Chunked recording (3 chunks)
# ══════════════════════════════════════════════════════════════════════════════

class TestChunkedRecording:
    def test_transcribe_3_chunks_concat(self, tmp_path):
        """transcribe_chunks() với 3 file nhỏ → concat kết quả."""
        from src.services.transcription_service import transcribe_chunks

        texts = ["Phần một.", "Phần hai.", "Phần ba."]
        chunk_files = []
        for i, _ in enumerate(texts):
            f = tmp_path / f"chunk{i:03d}.wav"
            f.write_bytes(b"\x00" * 100)
            chunk_files.append(str(f))

        with patch(
            "src.services.transcription_service.transcribe",
            side_effect=texts,
        ):
            result = transcribe_chunks(chunk_files)

        assert result == "Phần một. Phần hai. Phần ba."

    def test_failed_chunk_skipped_rest_continues(self, tmp_path):
        """Chunk thất bại không làm dừng toàn bộ — các chunk khác vẫn transcribe."""
        from src.services.transcription_service import transcribe_chunks

        def _side_effect(path, language="en"):
            if "bad" in path:
                raise RuntimeError("chunk fail")
            return "ok"

        files = [
            str(tmp_path / "good1.wav"),
            str(tmp_path / "bad.wav"),
            str(tmp_path / "good2.wav"),
        ]
        for f in files:
            (tmp_path / f.split("\\")[-1].split("/")[-1]).write_bytes(b"\x00" * 10)

        with patch("src.services.transcription_service.transcribe", side_effect=_side_effect):
            result = transcribe_chunks(files)

        assert result == "ok ok"

    def test_audio_recorder_chunk_state_reset_on_start(self):
        """AudioRecorder reset _completed_chunks khi gọi start() mới."""
        import threading
        from src.modules.audio_recorder import AudioRecorder

        rec = AudioRecorder()
        rec._completed_chunks = ["/old/chunk.wav"]

        with patch.object(rec, "_record_loop"):
            fake_thread = MagicMock(spec=threading.Thread)
            fake_thread.is_alive.return_value = True
            with patch("threading.Thread", return_value=fake_thread):
                rec.start(output_path="/tmp/new_recording.wav")

        assert rec.get_completed_chunks() == []
