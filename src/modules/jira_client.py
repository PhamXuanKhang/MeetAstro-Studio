"""
Jira REST API client for pushing action items.

Automatically enters stub mode if credentials are missing.
Creates Epic -> Task -> Subtask hierarchy via Jira REST API v3.
"""
from typing import Any, Optional

import httpx

from src.config import get_logger, get_settings
from src.schema import Epic, Subtask, Task

logger = get_logger(__name__)

_STUB_KEY = "STUB-001"
_SKIP_VALUES = ("N/A", "TBD", "None", "Unassigned")


class JiraClient:
    """
    Client for pushing action items to Jira.

    Automatically enters stub mode if credentials are missing.
    In stub mode, operations are logged but no actual API calls are made.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        email: Optional[str] = None,
        token: Optional[str] = None,
        project_key: Optional[str] = None,
        allow_stub: bool = True,
    ) -> None:
        """
        Initialize Jira client.

        Args:
            base_url: Jira base URL. If None, loads from settings.
            email: Jira user email. If None, loads from settings.
            token: Jira API token. If None, loads from settings.
            project_key: Jira project key. If None, loads from settings.
        """
        settings = get_settings()
        self._base_url = (base_url if base_url is not None else settings.jira_base_url).rstrip("/")
        self._email = email if email is not None else settings.jira_email
        self._token = token if token is not None else settings.jira_api_token
        self._project_key = project_key if project_key is not None else settings.jira_project_key
        self._stub = not (self._base_url and self._email and self._token and self._project_key)

        if self._stub:
            if not allow_stub:
                missing = []
                if not self._base_url:
                    missing.append("base_url")
                if not self._email:
                    missing.append("email")
                if not self._token:
                    missing.append("token")
                if not self._project_key:
                    missing.append("project_key")
                raise ValueError(
                    "Jira credentials are not configured: "
                    + ", ".join(missing)
                )
            logger.warning("Jira credentials missing - running in STUB mode (no actual API calls).")

    @property
    def is_stub(self) -> bool:
        """Return True if client is in stub mode."""
        return self._stub

    @property
    def base_url(self) -> str:
        """Return normalized Jira base URL."""
        return self._base_url

    def _headers(self) -> dict:
        """Return HTTP headers for Jira API requests."""
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _parse_error(self, response: httpx.Response) -> str:
        """Parse error details from Jira response."""
        try:
            body = response.json()
            error_messages = body.get("errorMessages") or []
            field_errors = body.get("errors") or {}
            parts = []
            if error_messages:
                parts.append("; ".join(error_messages))
            if field_errors:
                parts.append("; ".join(f"{k}: {v}" for k, v in field_errors.items()))
            return " | ".join(parts) if parts else response.text[:300]
        except Exception:
            return response.text[:300]

    def _post(self, payload: dict) -> str:
        """
        Send POST request to Jira Issues API.

        Uses sync httpx.Client to allow calling from Celery workers
        running inside asyncio.run() without nested event loops.

        Returns:
            Issue key (e.g., "MEET-123")
        """
        url = f"{self._base_url}/rest/api/3/issue"
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                url,
                json=payload,
                headers=self._headers(),
                auth=(self._email, self._token),
            )
        if response.status_code >= 400:
            detail = self._parse_error(response)
            logger.error(
                "Jira API returned error %s: %s",
                response.status_code,
                detail,
            )
            raise RuntimeError(f"{response.status_code} Client Error: {detail}")
        return response.json().get("key", _STUB_KEY)

    def create_epic(self, epic: Epic) -> str:
        """
        Create an Epic in Jira.

        Args:
            epic: Epic data to create.

        Returns:
            Issue key (e.g., "MEET-1")
        """
        if self._stub:
            logger.info("[STUB] Creating Epic: '%s'", epic.summary)
            return _STUB_KEY

        payload: dict[str, Any] = {
            "fields": {
                "project": {"key": self._project_key},
                "summary": epic.summary,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [{
                        "type": "paragraph",
                        "content": [{"type": "text", "text": epic.description}]
                    }],
                },
                "issuetype": {"name": "Epic"},
            }
        }
        key = self._post(payload)
        logger.info("Created Epic %s: '%s'.", key, epic.summary)
        return key

    def create_task(self, task: Task, epic_key: str) -> str:
        """
        Create a Task under an Epic.

        Args:
            task: Task data to create.
            epic_key: Parent Epic key.

        Returns:
            Issue key
        """
        if self._stub:
            logger.info("[STUB] Creating Task: '%s' (epic=%s)", task.summary, epic_key)
            return _STUB_KEY

        payload: dict[str, Any] = {
            "fields": {
                "project": {"key": self._project_key},
                "summary": task.summary,
                "issuetype": {"name": "Task"},
                "parent": {"key": epic_key},
                "priority": {"name": task.priority.value},
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [{
                        "type": "paragraph",
                        "content": [{"type": "text", "text": task.context}]
                    }],
                },
            }
        }

        if task.deadline and task.deadline not in _SKIP_VALUES and "-" in task.deadline:
            payload["fields"]["duedate"] = task.deadline

        if task.assignee and task.assignee not in _SKIP_VALUES:
            payload["fields"]["assignee"] = {"name": task.assignee}

        key = self._post(payload)
        logger.info("Created Task %s: '%s'.", key, task.summary)
        return key

    def create_subtask(self, subtask: Subtask, task_key: str) -> str:
        """
        Create a Subtask under a Task.

        Args:
            subtask: Subtask data to create.
            task_key: Parent Task key.

        Returns:
            Issue key
        """
        if self._stub:
            logger.info("[STUB] Creating Subtask: '%s' (task=%s)", subtask.summary, task_key)
            return _STUB_KEY

        payload: dict[str, Any] = {
            "fields": {
                "project": {"key": self._project_key},
                "summary": subtask.summary,
                "issuetype": {"name": "Subtask"},
                "parent": {"key": task_key},
                "priority": {"name": subtask.priority.value},
            }
        }

        if subtask.deadline and subtask.deadline not in _SKIP_VALUES and "-" in subtask.deadline:
            payload["fields"]["duedate"] = subtask.deadline

        if subtask.assignee and subtask.assignee not in _SKIP_VALUES:
            payload["fields"]["assignee"] = {"name": subtask.assignee}

        key = self._post(payload)
        logger.info("Created Subtask %s: '%s'.", key, subtask.summary)
        return key
