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


def normalize_jira_credentials(config: Optional[dict[str, str]]) -> dict[str, str]:
    """Normalize Jira provider config keys and fail if required values are missing."""
    config = config or {}
    credentials = {
        "base_url": (
            config.get("base_url")
            or config.get("jira_base_url")
            or config.get("url")
            or config.get("site_url")
            or ""
        ),
        "email": config.get("email") or config.get("jira_email") or "",
        "token": (
            config.get("token")
            or config.get("api_key")
            or config.get("api_token")
            or config.get("jira_api_token")
            or ""
        ),
        "project_key": (
            config.get("project_key")
            or config.get("projectKey")
            or config.get("jira_project_key")
            or ""
        ),
    }
    credentials = {key: value.strip() for key, value in credentials.items()}
    missing = [key for key, value in credentials.items() if not value]
    if missing:
        raise ValueError(
            "Jira credentials are not configured: " + ", ".join(missing)
        )
    return credentials


def push_analysis_to_jira(
    analysis: MeetingAnalysis,
    *,
    credentials: Optional[dict[str, str]] = None,
    client: Optional[JiraClient] = None,
    allow_stub: bool = True,
) -> JiraPushResult:
    """
    Push entire Epic -> Task -> Subtask hierarchy from MeetingAnalysis to Jira.

    Args:
        analysis: MeetingAnalysis containing epics to push.
        credentials: Jira credentials dict with keys: base_url, email, token, project_key.
                     Loaded from provider_configs in jira_push_task via Fernet decrypt.
        client: Optional JiraClient instance. If None, created from credentials.

    Returns:
        JiraPushResult with counts and keys.

    Raises:
        ValueError: If no epics to push.
        RuntimeError: If any Jira API call fails.
    """
    if not analysis.epics:
        raise ValueError("No epics to push to Jira.")

    if client is None:
        if credentials:
            credentials = normalize_jira_credentials(credentials)
            client = JiraClient(
                base_url=credentials["base_url"],
                email=credentials["email"],
                token=credentials["token"],
                project_key=credentials["project_key"],
                allow_stub=allow_stub,
            )
        else:
            client = JiraClient(allow_stub=allow_stub)

    result = JiraPushResult(is_stub=client.is_stub)

    for epic in analysis.epics:
        try:
            epic_key = client.create_epic(epic)
        except Exception as exc:
            raise RuntimeError(f"Failed to create Epic ('{epic.summary}'): {exc}") from exc

        result.epic_keys.append(epic_key)
        result.epic_count += 1

        for task in epic.tasks:
            try:
                task_key = client.create_task(task, epic_key)
            except Exception as exc:
                raise RuntimeError(f"Failed to create Task ('{task.summary}'): {exc}") from exc

            result.task_count += 1

            for subtask in task.subtasks:
                try:
                    client.create_subtask(subtask, task_key)
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
