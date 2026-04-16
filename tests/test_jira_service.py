"""Tests cho jira_service — orchestration Epic -> Task -> Subtask."""
from unittest.mock import MagicMock

import pytest

from src.schema import Epic, MeetingAnalysis, Priority, Subtask, Task
from src.services.jira_service import JiraPushResult, push_analysis_to_jira


def _make_analysis() -> MeetingAnalysis:
    subtasks = [
        Subtask(
            summary="Chuẩn bị tài liệu",
            assignee="Nam",
            deadline="2024-01-10",
            priority=Priority.MEDIUM,
            context="context subtask",
        )
    ]
    tasks = [
        Task(
            summary="Triển khai",
            assignee="Alice",
            deadline="2024-01-15",
            priority=Priority.HIGH,
            context="context task",
            subtasks=subtasks,
        )
    ]
    epics = [Epic(summary="Ra mắt Q1", description="Chuẩn bị launch", tasks=tasks)]
    return MeetingAnalysis(summary="summary", epics=epics)


def test_push_analysis_to_jira_raises_on_empty_epics():
    analysis = MeetingAnalysis(summary="no epics", epics=[])

    with pytest.raises(ValueError, match="Không có epics"):
        push_analysis_to_jira(analysis)


def test_push_analysis_to_jira_returns_counts_and_keys():
    analysis = _make_analysis()
    client = MagicMock()
    client.is_stub = False
    client.create_epic.return_value = "MEET-1"
    client.create_task.return_value = "MEET-2"

    result = push_analysis_to_jira(analysis, client=client)

    assert isinstance(result, JiraPushResult)
    assert result.is_stub is False
    assert result.epic_keys == ["MEET-1"]
    assert result.epic_count == 1
    assert result.task_count == 1
    assert result.subtask_count == 1

    client.create_epic.assert_called_once_with(analysis.epics[0])
    client.create_task.assert_called_once_with(analysis.epics[0].tasks[0], "MEET-1")
    client.create_subtask.assert_called_once_with(analysis.epics[0].tasks[0].subtasks[0], "MEET-2")


def test_push_analysis_to_jira_propagates_stub_mode():
    analysis = _make_analysis()
    client = MagicMock()
    client.is_stub = True
    client.create_epic.return_value = "STUB-001"
    client.create_task.return_value = "STUB-001"

    result = push_analysis_to_jira(analysis, client=client)

    assert result.is_stub is True
    assert result.epic_keys == ["STUB-001"]


def test_push_analysis_to_jira_wraps_task_error_with_context():
    analysis = _make_analysis()
    client = MagicMock()
    client.is_stub = False
    client.create_epic.return_value = "MEET-1"
    client.create_task.side_effect = RuntimeError("Jira unavailable")

    with pytest.raises(RuntimeError, match="Tạo Task thất bại"):
        push_analysis_to_jira(analysis, client=client)
