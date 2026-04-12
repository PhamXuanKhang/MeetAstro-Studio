"""
Jira REST API client — stub mode nếu thiếu credentials.
Tạo Epic → Task → Subtask qua Jira REST API v3.
"""
import requests

from src.config import JIRA_API_TOKEN, JIRA_BASE_URL, JIRA_PROJECT_KEY, get_logger
from src.schema import Epic, Subtask, Task

logger = get_logger(__name__)

_STUB_KEY = "STUB-001"


class JiraClient:
    """Client gửi action items lên Jira. Tự động vào stub mode nếu thiếu credentials."""

    def __init__(
        self,
        base_url: str = JIRA_BASE_URL,
        token: str = JIRA_API_TOKEN,
        project_key: str = JIRA_PROJECT_KEY,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._project_key = project_key
        self._stub = not (base_url and token and project_key)
        if self._stub:
            logger.warning("Jira credentials thiếu — đang chạy STUB mode (không gửi API thật).")

    @property
    def is_stub(self) -> bool:
        return self._stub

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _post(self, payload: dict) -> str:
        """Gửi POST tới Jira Issues API. Trả về issue key."""
        url = f"{self._base_url}/rest/api/3/issue"
        response = requests.post(url, json=payload, headers=self._headers(), timeout=10)
        response.raise_for_status()
        return response.json().get("key", _STUB_KEY)

    def create_epic(self, epic: Epic) -> str:
        """Tạo Epic trên Jira. Trả về issue key (vd: MEET-1)."""
        if self._stub:
            logger.info("[STUB] Tạo Epic: '%s'", epic.summary)
            return _STUB_KEY

        payload = {
            "fields": {
                "project": {"key": self._project_key},
                "summary": epic.summary,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [{"type": "paragraph", "content": [{"type": "text", "text": epic.description}]}],
                },
                "issuetype": {"name": "Epic"},
                "customfield_10014": epic.summary,  # Epic Name field
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

        payload = {
            "fields": {
                "project": {"key": self._project_key},
                "summary": task.summary,
                "issuetype": {"name": "Task"},
                "customfield_10014": epic_key,  # Epic Link
                "priority": {"name": task.priority.value},
                "duedate": task.deadline,
                "assignee": {"name": task.assignee} if task.assignee else None,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [{"type": "paragraph", "content": [{"type": "text", "text": task.context}]}],
                },
            }
        }
        key = self._post(payload)
        logger.info("Đã tạo Task %s: '%s'.", key, task.summary)
        return key

    def create_subtask(self, subtask: Subtask, task_key: str) -> str:
        """Tạo Subtask dưới Task. Trả về issue key."""
        if self._stub:
            logger.info("[STUB] Tạo Subtask: '%s' (task=%s)", subtask.summary, task_key)
            return _STUB_KEY

        payload = {
            "fields": {
                "project": {"key": self._project_key},
                "summary": subtask.summary,
                "issuetype": {"name": "Subtask"},
                "parent": {"key": task_key},
                "priority": {"name": subtask.priority.value},
                "duedate": subtask.deadline,
                "assignee": {"name": subtask.assignee} if subtask.assignee else None,
            }
        }
        key = self._post(payload)
        logger.info("Đã tạo Subtask %s: '%s'.", key, subtask.summary)
        return key
