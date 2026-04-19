"""
Jira REST API client — stub mode nếu thiếu credentials.
Tạo Epic → Task → Subtask qua Jira REST API v3.
"""
import asyncio
from typing import Any, Optional

import httpx

from src.config import JIRA_API_TOKEN, JIRA_BASE_URL, JIRA_EMAIL, JIRA_PROJECT_KEY, get_logger
from src.schema import Epic, Subtask, Task

logger = get_logger(__name__)

_STUB_KEY = "STUB-001"
_SKIP_VALUES = ("N/A", "TBD", "None", "Unassigned")


class JiraClient:
    """Client gửi action items lên Jira. Tự động vào stub mode nếu thiếu credentials."""

    def __init__(
        self,
        base_url: str = JIRA_BASE_URL,
        email: str = JIRA_EMAIL,
        token: str = JIRA_API_TOKEN,
        project_key: str = JIRA_PROJECT_KEY,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._email = email
        self._token = token
        self._project_key = project_key
        self._stub = not (base_url and email and token and project_key)
        if self._stub:
            logger.warning("Jira credentials thiếu — đang chạy STUB mode (không gửi API thật).")

    @property
    def is_stub(self) -> bool:
        return self._stub

    def _headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _parse_error(self, response: httpx.Response) -> str:
        """Parse lỗi từ Jira response — errorMessages + errors dict."""
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

    async def _post_async(self, payload: dict) -> str:
        """Gửi POST async tới Jira Issues API. Trả về issue key."""
        url = f"{self._base_url}/rest/api/3/issue"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                url,
                json=payload,
                headers=self._headers(),
                auth=(self._email, self._token),
            )
        if response.status_code >= 400:
            detail = self._parse_error(response)
            logger.error(
                "Jira API trả về lỗi %s: %s",
                response.status_code,
                detail,
            )
            raise RuntimeError(f"{response.status_code} Client Error: {detail}")
        return response.json().get("key", _STUB_KEY)

    def _post(self, payload: dict) -> str:
        """Sync wrapper cho _post_async."""
        return asyncio.run(self._post_async(payload))

    def create_epic(self, epic: Epic) -> str:
        """Tạo Epic trên Jira. Trả về issue key (vd: MEET-1)."""
        if self._stub:
            logger.info("[STUB] Tạo Epic: '%s'", epic.summary)
            return _STUB_KEY

        payload: dict[str, Any] = {
            "fields": {
                "project": {"key": self._project_key},
                "summary": epic.summary,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [{"type": "paragraph", "content": [{"type": "text", "text": epic.description}]}],
                },
                "issuetype": {"name": "Epic"},
            }
        }
        key = self._post(payload)
        logger.info("Đã tạo Epic %s: '%s'.", key, epic.summary)
        return key

    def create_task(self, task: Task, epic_key: str) -> str:
        """Tạo Task dưới Epic. Trả về issue key."""
        if self._stub:
            logger.info("[STUB] Tạo Task: '%s' (epic=%s)", task.summary, epic_key)
            return _STUB_KEY

        payload: dict[str, Any] = {
            "fields": {
                "project": {"key": self._project_key},
                "summary": task.summary,
                "issuetype": {"name": "Task"},
                "customfield_10014": epic_key,
                "priority": {"name": task.priority.value},
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [{"type": "paragraph", "content": [{"type": "text", "text": task.context}]}],
                },
            }
        }

        if task.deadline and task.deadline not in _SKIP_VALUES and "-" in task.deadline:
            payload["fields"]["duedate"] = task.deadline

        if task.assignee and task.assignee not in _SKIP_VALUES:
            payload["fields"]["assignee"] = {"name": task.assignee}

        key = self._post(payload)
        logger.info("Đã tạo Task %s: '%s'.", key, task.summary)
        return key

    def create_subtask(self, subtask: Subtask, task_key: str) -> str:
        """Tạo Subtask dưới Task. Trả về issue key."""
        if self._stub:
            logger.info("[STUB] Tạo Subtask: '%s' (task=%s)", subtask.summary, task_key)
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
        logger.info("Đã tạo Subtask %s: '%s'.", key, subtask.summary)
        return key
