"""
Celery task: push approved action items to Jira.

Input:  meeting_id (str)
Output: item-level push summary.
"""
from __future__ import annotations

from typing import Any

from src.config import get_logger
from src.db.crud.meeting_crud import get_meeting, update_meeting_status
from src.db.crud.provider_crud import get_provider_config
from src.db.crud.review_crud import list_review_items, update_action_item_sync
from src.modules.jira_client import JiraClient
from src.schema import Epic, Priority, Subtask, Task
from src.services.jira_service import normalize_jira_credentials
from src.workers.celery_app import celery_app

logger = get_logger(__name__)

FALLBACK_EPIC_SUMMARY = "Action Items"


@celery_app.task(
    name="push_to_jira",
    bind=True,
    max_retries=0,
    queue="default",
)
def push_to_jira(self, meeting_id: str) -> dict:
    """Push unsynced approved items to Jira with best-effort item status updates."""
    logger.info("[jira_push_task] Starting Jira push for meeting %s", meeting_id)

    meeting = get_meeting(meeting_id)
    if not meeting:
        raise ValueError(f"Meeting {meeting_id} not found.")

    user_id = meeting.get("user_id")
    if not user_id:
        update_meeting_status(
            meeting_id, status="failed", error_message="Meeting has no user_id."
        )
        raise ValueError(f"Meeting {meeting_id} has no user_id.")

    try:
        jira_config = get_provider_config("jira", user_id=user_id)
        credentials = normalize_jira_credentials(jira_config)
        client = JiraClient(
            base_url=credentials["base_url"],
            email=credentials["email"],
            token=credentials["token"],
            project_key=credentials["project_key"],
            allow_stub=False,
        )
    except Exception as exc:
        message = str(exc)
        update_meeting_status(meeting_id, status="failed", error_message=message)
        raise ValueError(message) from exc

    all_items = list_review_items(meeting_id)
    approved_items = [
        item for item in all_items if item.get("review_status") == "approved"
    ]
    pushable_items = [
        item for item in approved_items if item.get("sync_status") != "synced"
    ]
    skipped_synced = len(approved_items) - len(pushable_items)

    if not approved_items:
        update_meeting_status(
            meeting_id, status="failed", error_message="No approved items to push."
        )
        raise ValueError("No approved items to push.")

    if not pushable_items:
        update_meeting_status(meeting_id, status="pushed")
        return {
            "epic_keys": [],
            "task_count": 0,
            "subtask_count": 0,
            "synced_count": 0,
            "failed_count": 0,
            "skipped_synced_count": skipped_synced,
            "is_stub": False,
        }

    context = _PushContext(client=client, base_url=credentials["base_url"], items=all_items)
    for item in pushable_items:
        if item.get("item_type") == "epic":
            context.ensure_epic(item)
        elif item.get("item_type") == "task":
            context.ensure_task(item)
        elif item.get("item_type") == "subtask":
            context.ensure_subtask(item)
        else:
            context.fail_item(item, f"Unsupported item_type: {item.get('item_type')}")

    if context.synced_count > 0 and context.failed_count == 0:
        final_status = "pushed"
    elif context.synced_count > 0:
        final_status = "partial_success"
    else:
        final_status = "failed"

    error_message = None
    if final_status == "failed":
        error_message = "All Jira pushes failed. Check item sync_error values."
    elif final_status == "partial_success":
        error_message = "Some Jira items failed. Check item sync_error values."

    update_meeting_status(meeting_id, status=final_status, error_message=error_message)

    logger.info(
        "[jira_push_task] Complete: synced=%d failed=%d skipped=%d status=%s",
        context.synced_count,
        context.failed_count,
        skipped_synced,
        final_status,
    )
    return {
        "epic_keys": context.epic_keys,
        "task_count": context.task_count,
        "subtask_count": context.subtask_count,
        "synced_count": context.synced_count,
        "failed_count": context.failed_count,
        "skipped_synced_count": skipped_synced,
        "is_stub": False,
    }


class _PushContext:
    """Stateful best-effort Jira pusher for one meeting."""

    def __init__(self, *, client: JiraClient, base_url: str, items: list[dict[str, Any]]) -> None:
        self.client = client
        self.base_url = base_url.rstrip("/")
        self.items_by_id = {str(item["id"]): item for item in items}
        self.created_keys: dict[str, str] = {}
        self.fallback_epic_key: str | None = None
        self.failed_ids: set[str] = set()
        self.epic_keys: list[str] = []
        self.task_count = 0
        self.subtask_count = 0
        self.synced_count = 0
        self.failed_count = 0

    def issue_url(self, issue_key: str) -> str:
        return f"{self.base_url}/browse/{issue_key}"

    def existing_key(self, item: dict[str, Any]) -> str | None:
        if item.get("sync_status") == "synced" and item.get("jira_issue_key"):
            return str(item["jira_issue_key"])
        return self.created_keys.get(str(item["id"]))

    def mark_syncing(self, item: dict[str, Any]) -> None:
        update_action_item_sync(str(item["id"]), sync_status="syncing", sync_error="")
        item["sync_status"] = "syncing"
        item["sync_error"] = ""

    def mark_synced(self, item: dict[str, Any], issue_key: str) -> None:
        update_action_item_sync(
            str(item["id"]),
            sync_status="synced",
            sync_error="",
            jira_issue_key=issue_key,
            jira_issue_url=self.issue_url(issue_key),
        )
        item["sync_status"] = "synced"
        item["sync_error"] = ""
        item["jira_issue_key"] = issue_key
        item["jira_issue_url"] = self.issue_url(issue_key)
        self.created_keys[str(item["id"])] = issue_key
        self.synced_count += 1

    def fail_item(self, item: dict[str, Any], message: str) -> None:
        logger.warning("[jira_push_task] Item %s failed: %s", item.get("id"), message)
        item_id = str(item["id"])
        update_action_item_sync(
            item_id,
            sync_status="failed",
            sync_error=message,
        )
        item["sync_status"] = "failed"
        item["sync_error"] = message
        if item_id not in self.failed_ids:
            self.failed_ids.add(item_id)
            self.failed_count += 1

    def ensure_epic(self, item: dict[str, Any]) -> str | None:
        existing = self.existing_key(item)
        if existing:
            return existing
        if item.get("review_status") != "approved":
            return None
        if item.get("sync_status") == "synced":
            return None

        try:
            self.mark_syncing(item)
            epic = Epic(
                summary=item.get("title") or "",
                description=item.get("description") or "",
            )
            issue_key = self.client.create_epic(epic)
            self.mark_synced(item, issue_key)
            self.epic_keys.append(issue_key)
            return issue_key
        except Exception as exc:
            self.fail_item(item, str(exc))
            return None

    def ensure_fallback_epic(self) -> str:
        if self.fallback_epic_key:
            return self.fallback_epic_key
        epic = Epic(
            summary=FALLBACK_EPIC_SUMMARY,
            description="Approved action items without a pushable parent epic.",
        )
        self.fallback_epic_key = self.client.create_epic(epic)
        self.epic_keys.append(self.fallback_epic_key)
        return self.fallback_epic_key

    def parent_epic_key_for_task(self, item: dict[str, Any]) -> str | None:
        parent_id = item.get("parent_id")
        if not parent_id:
            return self.ensure_fallback_epic()

        parent = self.items_by_id.get(str(parent_id))
        if not parent or parent.get("item_type") != "epic":
            return self.ensure_fallback_epic()

        existing = self.existing_key(parent)
        if existing:
            return existing

        if parent.get("review_status") == "approved" and parent.get("sync_status") != "synced":
            return self.ensure_epic(parent)

        return self.ensure_fallback_epic()

    def ensure_task(self, item: dict[str, Any]) -> str | None:
        existing = self.existing_key(item)
        if existing:
            return existing
        if item.get("review_status") != "approved":
            return None
        if item.get("sync_status") == "synced":
            return None

        try:
            epic_key = self.parent_epic_key_for_task(item)
            if not epic_key:
                self.fail_item(item, "Cannot resolve parent Epic for task.")
                return None
            self.mark_syncing(item)
            task = Task(
                summary=item.get("title") or "",
                assignee=item.get("assignee"),
                deadline=item.get("deadline"),
                priority=_priority(item.get("priority")),
                context=item.get("description") or "",
                subtasks=[],
            )
            issue_key = self.client.create_task(task, epic_key)
            self.mark_synced(item, issue_key)
            self.task_count += 1
            return issue_key
        except Exception as exc:
            self.fail_item(item, str(exc))
            return None

    def parent_task_key_for_subtask(self, item: dict[str, Any]) -> str | None:
        parent_id = item.get("parent_id")
        if not parent_id:
            return None

        parent = self.items_by_id.get(str(parent_id))
        if not parent or parent.get("item_type") != "task":
            return None

        existing = self.existing_key(parent)
        if existing:
            return existing

        if parent.get("review_status") == "approved" and parent.get("sync_status") != "synced":
            return self.ensure_task(parent)
        return None

    def ensure_subtask(self, item: dict[str, Any]) -> str | None:
        existing = self.existing_key(item)
        if existing:
            return existing
        if item.get("review_status") != "approved":
            return None
        if item.get("sync_status") == "synced":
            return None

        task_key = self.parent_task_key_for_subtask(item)
        if not task_key:
            self.fail_item(item, "Cannot resolve parent Task for subtask.")
            return None

        try:
            self.mark_syncing(item)
            subtask = Subtask(
                summary=item.get("title") or "",
                assignee=item.get("assignee"),
                deadline=item.get("deadline"),
                priority=_priority(item.get("priority")),
                context=item.get("description") or "",
            )
            issue_key = self.client.create_subtask(subtask, task_key)
            self.mark_synced(item, issue_key)
            self.subtask_count += 1
            return issue_key
        except Exception as exc:
            self.fail_item(item, str(exc))
            return None


def _priority(value: Any) -> Priority:
    """Coerce stored priority strings to schema Priority enum."""
    if value in {priority.value for priority in Priority}:
        return Priority(value)
    normalized = str(value or "").strip().lower()
    for priority in Priority:
        if priority.value.lower() == normalized:
            return priority
    return Priority.MEDIUM
