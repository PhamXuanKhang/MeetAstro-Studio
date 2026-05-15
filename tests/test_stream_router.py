import uuid
from types import SimpleNamespace

import pytest

from src.api.routers import stream
from src.services.stream_session_manager import _with_language_query
from src.workers.tasks import stream_finalize_task


class FakeSession:
    def __init__(self, *, lines=None, buffer="", ready=True):
        self.partial_lines = lines or []
        self.buffer_transcription = buffer
        self.ready = ready
        self.eof_sent = False
        self.wait_timeout = None

    async def send_eof(self):
        self.eof_sent = True

    async def wait_until_ready_to_stop(self, timeout_seconds):
        self.wait_timeout = timeout_seconds
        return self.ready


class FakeManager:
    def __init__(self, session):
        self.session = session
        self.closed = None

    async def get_session(self, meeting_id):
        return self.session

    async def close_session(self, meeting_id):
        self.closed = meeting_id


class FakeTask:
    id = "job-123"


@pytest.mark.asyncio
async def test_stop_waits_ready_and_persists_committed_lines(monkeypatch):
    meeting_id = uuid.uuid4()
    session = FakeSession(lines=[{
        "speaker": 0,
        "start": "00:00:01.000",
        "end": "00:00:02.000",
        "text": "hello",
    }])
    saved = []
    statuses = []

    monkeypatch.setattr(stream, "get_stream_manager", lambda: FakeManager(session))
    monkeypatch.setattr(stream, "get_settings", lambda: SimpleNamespace(stream_stop_timeout_seconds=30.0))
    monkeypatch.setattr(stream, "create_transcript_segments", lambda meeting, segments: saved.extend(segments) or segments)
    monkeypatch.setattr(stream, "update_meeting_status", lambda meeting, status, **kwargs: statuses.append(status))
    monkeypatch.setattr(stream.finalize_stream_recording, "delay", lambda *args, **kwargs: FakeTask())

    result = await stream.stop_stream(meeting_id, audio_path="local.wav", language="vi")

    assert session.eof_sent is True
    assert session.wait_timeout == 30.0
    assert result["ready_to_stop"] is True
    assert result["persisted_segments"] == 1
    assert result["transcript_source"] == "lines"
    assert result["job_id"] == "job-123"
    assert saved == [{"speaker": "Speaker 0", "start": 1.0, "end": 2.0, "text": "hello"}]
    assert statuses[0] == "transcribed"


@pytest.mark.asyncio
async def test_stop_persists_buffer_only_when_lines_empty(monkeypatch):
    meeting_id = uuid.uuid4()
    session = FakeSession(buffer="buffer text")
    saved = []

    monkeypatch.setattr(stream, "get_stream_manager", lambda: FakeManager(session))
    monkeypatch.setattr(stream, "get_settings", lambda: SimpleNamespace(stream_stop_timeout_seconds=30.0))
    monkeypatch.setattr(stream, "create_transcript_segments", lambda meeting, segments: saved.extend(segments) or segments)
    monkeypatch.setattr(stream, "update_meeting_status", lambda *args, **kwargs: None)
    monkeypatch.setattr(stream.finalize_stream_recording, "delay", lambda *args, **kwargs: FakeTask())

    result = await stream.stop_stream(meeting_id, audio_path=None, language=None)

    assert result["transcript_source"] == "buffer"
    assert result["job_id"] == "job-123"
    assert saved == [{"speaker": "Speaker ?", "start": 0.0, "end": 0.0, "text": "buffer text"}]


@pytest.mark.asyncio
async def test_stop_empty_snapshot_queues_fallback(monkeypatch):
    meeting_id = uuid.uuid4()
    session = FakeSession(lines=[], buffer="", ready=False)
    statuses = []
    queued = {}

    monkeypatch.setattr(stream, "get_stream_manager", lambda: FakeManager(session))
    monkeypatch.setattr(stream, "get_settings", lambda: SimpleNamespace(stream_stop_timeout_seconds=30.0))
    monkeypatch.setattr(stream, "create_transcript_segments", lambda meeting, segments: segments)
    monkeypatch.setattr(stream, "update_meeting_status", lambda meeting, status, **kwargs: statuses.append(status))

    def fake_delay(meeting_id_arg, **kwargs):
        queued["meeting_id"] = meeting_id_arg
        queued.update(kwargs)
        return FakeTask()

    monkeypatch.setattr(stream.finalize_stream_recording, "delay", fake_delay)

    result = await stream.stop_stream(meeting_id, audio_path="local.wav", language="vi")

    assert result["ready_to_stop"] is False
    assert result["transcript_source"] == "empty"
    assert result["persisted_segments"] == 0
    assert statuses == ["processing"]
    assert queued == {"meeting_id": str(meeting_id), "audio_path": "local.wav", "language": "vi"}


def test_language_query_merge():
    assert _with_language_query("ws://localhost:8000/asr?mode=full", "vi") == "ws://localhost:8000/asr?mode=full&language=vi"
    assert _with_language_query("ws://localhost:8000/asr?mode=full", "auto") == "ws://localhost:8000/asr?mode=full"


def test_finalize_uses_existing_segments(monkeypatch):
    statuses = []
    monkeypatch.setattr(stream_finalize_task, "get_transcript_segments", lambda meeting_id: [{"id": "seg"}])
    monkeypatch.setattr(stream_finalize_task, "update_meeting_status", lambda meeting_id, status, **kwargs: statuses.append(status))

    result = stream_finalize_task.finalize_stream_recording.run("meeting-1")

    assert result == {"status": "transcribed", "source": "whisper_livekit", "segment_count": 1}
    assert statuses == ["transcribed"]


def test_finalize_missing_key_fails_when_fallback_needed(monkeypatch):
    updates = []
    monkeypatch.setattr(stream_finalize_task, "get_transcript_segments", lambda meeting_id: [])
    monkeypatch.setattr(stream_finalize_task, "get_settings", lambda: SimpleNamespace(openai_api_key=""))
    monkeypatch.setattr(stream_finalize_task, "update_meeting_status", lambda meeting_id, status, **kwargs: updates.append((status, kwargs.get("error_message"))))

    result = stream_finalize_task.finalize_stream_recording.run("meeting-1", audio_path="local.wav")

    assert result["status"] == "failed"
    assert result["source"] == "openai"
    assert updates[0] == ("processing", None)
    assert updates[1][0] == "failed"
