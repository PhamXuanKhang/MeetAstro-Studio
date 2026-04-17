"""
Jira service — orchestration luồng đẩy MeetingAnalysis lên Jira.
"""
from dataclasses import dataclass, field

from src.config import get_logger
from src.modules.jira_client import JiraClient
from src.schema import MeetingAnalysis

logger = get_logger(__name__)


@dataclass
class JiraPushResult:
    """Kết quả push một MeetingAnalysis lên Jira."""

    is_stub: bool
    epic_keys: list[str] = field(default_factory=list)
    epic_count: int = 0
    task_count: int = 0
    subtask_count: int = 0


def push_analysis_to_jira(
    analysis: MeetingAnalysis,
    client: JiraClient | None = None,
) -> JiraPushResult:
    """Đẩy toàn bộ Epic -> Task -> Subtask từ MeetingAnalysis lên Jira."""
    if not analysis.epics:
        raise ValueError("Không có epics để đẩy lên Jira.")

    jira_client = client or JiraClient()
    result = JiraPushResult(is_stub=jira_client.is_stub)

    for epic in analysis.epics:
        try:
            epic_key = jira_client.create_epic(epic)
        except Exception as exc:
            raise RuntimeError(f"Tạo Epic thất bại ('{epic.summary}'): {exc}") from exc

        result.epic_keys.append(epic_key)
        result.epic_count += 1

        for task in epic.tasks:
            try:
                task_key = jira_client.create_task(task, epic_key)
            except Exception as exc:
                raise RuntimeError(f"Tạo Task thất bại ('{task.summary}'): {exc}") from exc

            result.task_count += 1

            for subtask in task.subtasks:
                try:
                    jira_client.create_subtask(subtask, task_key)
                except Exception as exc:
                    raise RuntimeError(
                        f"Tạo Subtask thất bại ('{subtask.summary}'): {exc}"
                    ) from exc
                result.subtask_count += 1

    logger.info(
        "Jira push hoàn tất: epics=%d tasks=%d subtasks=%d stub=%s",
        result.epic_count,
        result.task_count,
        result.subtask_count,
        result.is_stub,
    )
    return result
