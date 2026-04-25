"""
Jira service - orchestrate pushing MeetingAnalysis to Jira.
"""
from dataclasses import dataclass, field
from typing import Optional

from src.config import get_logger
from src.modules.jira_client import JiraClient
from src.schema import MeetingAnalysis

logger = get_logger(__name__)


@dataclass
class JiraPushResult:
    """Result of pushing a MeetingAnalysis to Jira."""

    is_stub: bool
    epic_keys: list[str] = field(default_factory=list)
    epic_count: int = 0
    task_count: int = 0
    subtask_count: int = 0


def push_analysis_to_jira(
    analysis: MeetingAnalysis,
    client: Optional[JiraClient] = None,
) -> JiraPushResult:
    """
    Push entire Epic -> Task -> Subtask hierarchy from MeetingAnalysis to Jira.

    Args:
        analysis: MeetingAnalysis containing epics to push.
        client: Optional JiraClient instance. If None, creates new one.

    Returns:
        JiraPushResult with counts and keys.

    Raises:
        ValueError: If no epics to push.
        RuntimeError: If any Jira API call fails.
    """
    if not analysis.epics:
        raise ValueError("No epics to push to Jira.")

    jira_client = client or JiraClient()
    result = JiraPushResult(is_stub=jira_client.is_stub)

    for epic in analysis.epics:
        try:
            epic_key = jira_client.create_epic(epic)
        except Exception as exc:
            raise RuntimeError(f"Failed to create Epic ('{epic.summary}'): {exc}") from exc

        result.epic_keys.append(epic_key)
        result.epic_count += 1

        for task in epic.tasks:
            try:
                task_key = jira_client.create_task(task, epic_key)
            except Exception as exc:
                raise RuntimeError(f"Failed to create Task ('{task.summary}'): {exc}") from exc

            result.task_count += 1

            for subtask in task.subtasks:
                try:
                    jira_client.create_subtask(subtask, task_key)
                except Exception as exc:
                    raise RuntimeError(
                        f"Failed to create Subtask ('{subtask.summary}'): {exc}"
                    ) from exc
                result.subtask_count += 1

    logger.info(
        "Jira push complete: epics=%d tasks=%d subtasks=%d stub=%s",
        result.epic_count,
        result.task_count,
        result.subtask_count,
        result.is_stub,
    )
    return result
