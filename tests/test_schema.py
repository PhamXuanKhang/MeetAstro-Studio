"""Tests cho src/schema.py — dataclass construction và to_dict/from_dict round-trip."""
import json
from datetime import datetime

import pytest

from src.schema import Epic, MeetingAnalysis, MeetingRecord, Priority, Subtask, Task


def make_sample_analysis() -> MeetingAnalysis:
    subtask = Subtask(
        summary="Cài đặt môi trường",
        assignee="Nam",
        deadline="2024-01-10",
        priority=Priority.MEDIUM,
        context="Nam sẽ cài môi trường trước.",
    )
    task = Task(
        summary="Triển khai hệ thống",
        assignee="Nam",
        deadline="2024-01-15",
        priority=Priority.HIGH,
        context="Cần triển khai trước Tết.",
        subtasks=[subtask],
    )
    epic = Epic(
        summary="Ra mắt sản phẩm",
        description="Chuẩn bị cho buổi launch Q1.",
        tasks=[task],
    )
    return MeetingAnalysis(
        epics=[epic],
        summary="Cuộc họp thống nhất kế hoạch launch Q1.",
        created_at=datetime(2024, 1, 5, 10, 0, 0),
    )


class TestPriority:
    def test_values(self):
        assert Priority.CRITICAL.value == "Critical"
        assert Priority.HIGH.value == "High"
        assert Priority.MEDIUM.value == "Medium"
        assert Priority.LOW.value == "Low"

    def test_from_string(self):
        assert Priority("High") == Priority.HIGH


class TestSubtask:
    def test_construction(self):
        s = Subtask("Do X", "Alice", "2024-02-01", Priority.LOW, "context here")
        assert s.summary == "Do X"
        assert s.assignee == "Alice"
        assert s.priority == Priority.LOW

    def test_to_dict(self):
        s = Subtask("Do X", "Alice", "2024-02-01", Priority.LOW, "ctx")
        d = s.to_dict()
        assert d["summary"] == "Do X"
        assert d["priority"] == "Low"
        assert d["assignee"] == "Alice"

    def test_from_dict_round_trip(self):
        s = Subtask("Do X", None, None, Priority.MEDIUM, "ctx")
        s2 = Subtask.from_dict(s.to_dict())
        assert s2.summary == s.summary
        assert s2.assignee is None
        assert s2.priority == Priority.MEDIUM


class TestTask:
    def test_default_subtasks_empty(self):
        t = Task("Task A", None, None, Priority.HIGH, "ctx")
        assert t.subtasks == []

    def test_to_dict_includes_subtasks(self):
        sub = Subtask("S1", None, None, Priority.LOW, "c")
        t = Task("T1", "Bob", "2024-03-01", Priority.HIGH, "ctx", subtasks=[sub])
        d = t.to_dict()
        assert len(d["subtasks"]) == 1
        assert d["subtasks"][0]["summary"] == "S1"

    def test_from_dict_round_trip(self):
        sub = Subtask("S1", "Alice", "2024-02-01", Priority.MEDIUM, "c")
        t = Task("T1", "Bob", "2024-03-01", Priority.HIGH, "ctx", subtasks=[sub])
        t2 = Task.from_dict(t.to_dict())
        assert t2.summary == "T1"
        assert len(t2.subtasks) == 1
        assert t2.subtasks[0].summary == "S1"


class TestEpic:
    def test_default_tasks_empty(self):
        e = Epic("E1", "desc")
        assert e.tasks == []

    def test_to_dict_from_dict(self):
        task = Task("T1", None, None, Priority.MEDIUM, "ctx")
        e = Epic("E1", "desc", tasks=[task])
        e2 = Epic.from_dict(e.to_dict())
        assert e2.summary == "E1"
        assert len(e2.tasks) == 1


class TestMeetingAnalysis:
    def test_to_dict_has_required_keys(self):
        analysis = make_sample_analysis()
        d = analysis.to_dict()
        assert "summary" in d
        assert "epics" in d
        assert "created_at" in d

    def test_to_json_valid_json(self):
        analysis = make_sample_analysis()
        s = analysis.to_json()
        parsed = json.loads(s)
        assert parsed["summary"] == analysis.summary

    def test_from_dict_round_trip(self):
        analysis = make_sample_analysis()
        analysis2 = MeetingAnalysis.from_dict(analysis.to_dict())
        assert analysis2.summary == analysis.summary
        assert len(analysis2.epics) == 1
        assert analysis2.epics[0].summary == "Ra mắt sản phẩm"
        assert analysis2.epics[0].tasks[0].subtasks[0].summary == "Cài đặt môi trường"

    def test_from_json_round_trip(self):
        analysis = make_sample_analysis()
        analysis2 = MeetingAnalysis.from_json(analysis.to_json())
        assert analysis2.summary == analysis.summary

    def test_priority_preserved(self):
        analysis = make_sample_analysis()
        analysis2 = MeetingAnalysis.from_dict(analysis.to_dict())
        task = analysis2.epics[0].tasks[0]
        assert task.priority == Priority.HIGH
        assert task.subtasks[0].priority == Priority.MEDIUM


class TestMeetingRecord:
    def test_construction_minimal(self):
        r = MeetingRecord(title="Test", transcript="text")
        assert r.id is None
        assert r.analysis is None
        assert r.audio_path is None

    def test_to_dict_with_analysis(self):
        analysis = make_sample_analysis()
        r = MeetingRecord(title="Test", transcript="text", analysis=analysis)
        d = r.to_dict()
        assert d["title"] == "Test"
        assert d["analysis"]["summary"] == analysis.summary

    def test_to_dict_without_analysis(self):
        r = MeetingRecord(title="Test", transcript="text")
        d = r.to_dict()
        assert d["analysis"] is None
