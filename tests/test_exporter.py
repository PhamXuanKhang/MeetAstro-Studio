"""Tests cho exporter.py — Markdown, JSON, CSV."""
import csv
import io
import json

from src.modules.exporter import export_csv, export_json, export_markdown
from src.schema import Epic, MeetingAnalysis, Priority, Subtask, Task


def make_analysis() -> MeetingAnalysis:
    subtask = Subtask(
        summary="Cài môi trường", assignee="Nam", deadline="2024-01-10",
        priority=Priority.MEDIUM, context="context subtask"
    )
    task = Task(
        summary="Triển khai", assignee="Alice", deadline="2024-01-15",
        priority=Priority.HIGH, context="context task", subtasks=[subtask]
    )
    epic = Epic(summary="Ra mắt Q1", description="Chuẩn bị launch.", tasks=[task])
    return MeetingAnalysis(epics=[epic], summary="Họp về launch Q1.")


class TestExportMarkdown:
    def test_contains_summary(self):
        md = export_markdown(make_analysis())
        assert "Họp về launch Q1." in md

    def test_contains_epic_title(self):
        md = export_markdown(make_analysis())
        assert "Ra mắt Q1" in md

    def test_contains_task_title(self):
        md = export_markdown(make_analysis())
        assert "Triển khai" in md

    def test_contains_subtask_title(self):
        md = export_markdown(make_analysis())
        assert "Cài môi trường" in md

    def test_contains_assignee(self):
        md = export_markdown(make_analysis())
        assert "Alice" in md

    def test_contains_priority(self):
        md = export_markdown(make_analysis())
        assert "High" in md

    def test_returns_string(self):
        assert isinstance(export_markdown(make_analysis()), str)

    def test_empty_epics(self):
        analysis = MeetingAnalysis(epics=[], summary="Họp rỗng.")
        md = export_markdown(analysis)
        assert "Họp rỗng." in md


class TestExportJson:
    def test_valid_json(self):
        result = export_json(make_analysis())
        parsed = json.loads(result)
        assert "summary" in parsed
        assert "epics" in parsed

    def test_contains_all_fields(self):
        parsed = json.loads(export_json(make_analysis()))
        task = parsed["epics"][0]["tasks"][0]
        assert task["summary"] == "Triển khai"
        assert task["assignee"] == "Alice"
        assert task["priority"] == "High"
        assert task["deadline"] == "2024-01-15"

    def test_subtasks_included(self):
        parsed = json.loads(export_json(make_analysis()))
        subtasks = parsed["epics"][0]["tasks"][0]["subtasks"]
        assert len(subtasks) == 1
        assert subtasks[0]["summary"] == "Cài môi trường"


class TestExportCsv:
    def _parse_csv(self, csv_str: str) -> list[dict]:
        reader = csv.DictReader(io.StringIO(csv_str))
        return list(reader)

    def test_valid_csv_with_header(self):
        result = export_csv(make_analysis())
        rows = self._parse_csv(result)
        assert len(rows) >= 1

    def test_task_row_present(self):
        rows = self._parse_csv(export_csv(make_analysis()))
        task_rows = [r for r in rows if r["type"] == "Task"]
        assert len(task_rows) == 1
        assert task_rows[0]["summary"] == "Triển khai"

    def test_subtask_row_present(self):
        rows = self._parse_csv(export_csv(make_analysis()))
        sub_rows = [r for r in rows if r["type"] == "Subtask"]
        assert len(sub_rows) == 1
        assert sub_rows[0]["summary"] == "Cài môi trường"

    def test_epic_column_populated(self):
        rows = self._parse_csv(export_csv(make_analysis()))
        assert all(r["epic"] == "Ra mắt Q1" for r in rows)

    def test_priority_in_csv(self):
        rows = self._parse_csv(export_csv(make_analysis()))
        task_row = next(r for r in rows if r["type"] == "Task")
        assert task_row["priority"] == "High"

    def test_empty_epics_no_rows(self):
        analysis = MeetingAnalysis(epics=[], summary="Trống.")
        rows = self._parse_csv(export_csv(analysis))
        assert len(rows) == 0
