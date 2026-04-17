"""
Jira REST API client — stub mode nếu thiếu credentials.
Tạo Epic → Task → Subtask qua Jira REST API v3.
"""
import requests
from requests.auth import HTTPBasicAuth

from src.config import JIRA_API_TOKEN, JIRA_BASE_URL, JIRA_EMAIL, JIRA_PROJECT_KEY, get_logger
from src.schema import Epic, Subtask, Task

logger = get_logger(__name__)

_STUB_KEY = "STUB-001"


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

    def _post(self, payload: dict) -> str:
        """Gửi POST tới Jira Issues API. Trả về issue key."""
        url = f"{self._base_url}/rest/api/3/issue"
        response = requests.post(
            url,
            json=payload,
            headers=self._headers(),
            auth=HTTPBasicAuth(self._email, self._token),
            timeout=10,
        )
        if not response.ok:
            logger.error(
                "Jira API trả về lỗi %s: %s",
                response.status_code,
                response.text,
            )
            raise RuntimeError(f"{response.status_code} Client Error: {response.text}")
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
            }
        }
        # Thử thêm customfield_10011 nếu Jira bắt buộc trường "Epic Name" trên Jira cũ
        # payload["fields"]["customfield_10011"] = epic.summary
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
                "parent": {"key": epic_key},  # Dùng parent thay cho Epic Link (Jira Cloud API mới)
                "priority": {"name": task.priority.value},
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [{"type": "paragraph", "content": [{"type": "text", "text": task.context}]}],
                },
            }
        }
        
        # Chỉ truyền duedate nếu là format hợp lệ
        if task.deadline and task.deadline not in ("N/A", "TBD", "None") and "-" in task.deadline:
            payload["fields"]["duedate"] = task.deadline
            
        # Chỉ truyền assignee nếu có giá trị thực
        if task.assignee and task.assignee not in ("N/A", "TBD", "None"):
            # Lưu ý: Jira Cloud dùng accountId, không dùng name. Nếu lỗi tiếp, cần mapping lại assignee.
            payload["fields"]["assignee"] = {"name": task.assignee}
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
            }
        }
        
        # Chỉ truyền duedate nếu là format hợp lệ
        if subtask.deadline and subtask.deadline not in ("N/A", "TBD", "None") and "-" in subtask.deadline:
            payload["fields"]["duedate"] = subtask.deadline
            
        # Chỉ truyền assignee nếu có giá trị thực
        if subtask.assignee and subtask.assignee not in ("N/A", "TBD", "None"):
            payload["fields"]["assignee"] = {"name": subtask.assignee}
        key = self._post(payload)
        logger.info("Đã tạo Subtask %s: '%s'.", key, subtask.summary)
        return key
