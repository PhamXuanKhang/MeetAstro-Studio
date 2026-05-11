"""
Celery task: push approved action items to Jira.

Input:  meeting_id (str)
Output: {"epic_keys": list, "task_count": int, "subtask_count": int, "is_stub": bool}
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from src.config import get_logger
from src.db.crud.meeting_crud import update_meeting_status
from src.db.crud.review_crud import list_review_items
from src.services.jira_service import push_analysis_to_jira
from src.workers.celery_app import celery_app

if TYPE_CHECKING:
    from src.schema import MeetingAnalysis

logger = get_logger(__name__)


@celery_app.task(
    name="push_to_jira",
    bind=True,
    max_retries=2,
    default_retry_delay=10,
    queue="default",
)
def push_to_jira(self, meeting_id: str) -> dict:
    """Push approved items to Jira and update meeting status."""
    logger.info("[jira_push_task] Starting Jira push for meeting %s", meeting_id)

    items = list_review_items(meeting_id, status="approved")
    if not items:
        raise ValueError("No approved items to push.")

    meeting_analysis = _reconstruct_analysis(items)

    try:
        push_result = push_analysis_to_jira(meeting_analysis)
    except Exception as exc:
        update_meeting_status(meeting_id, status="failed", error_message=str(exc))
        raise self.retry(exc=exc)

    update_meeting_status(meeting_id, status="pushed")

    logger.info(
        "[jira_push_task] Complete: epic_keys=%s tasks=%d subtasks=%d",
        push_result.epic_keys,
        push_result.task_count,
        push_result.subtask_count,
    )
    return {
        "epic_keys": push_result.epic_keys,
        "task_count": push_result.task_count,
        "subtask_count": push_result.subtask_count,
        "is_stub": push_result.is_stub,
    }


def _reconstruct_analysis(approved_items: list[dict]) -> "MeetingAnalysis":  # noqa: F821
    """
    Reconstruct MeetingAnalysis from flat list of approved action_items.

    action_items has no `item_index` column, so we rebuild hierarchy using
    `parent_id` and `item_type`:
      - Epic items (item_type=epic, parent_id=None)
      - Task items (item_type=task, parent_id=None → top-level task)
      - Subtask items (item_type=subtask, parent_id → belongs to parent task)

    Edits are stored directly in title/assignee/deadline/priority (no edited_* fields).
    """
    from src.schema import Epic, MeetingAnalysis, Priority, Subtask, Task

    # Separate by item_type
    epics_raw = [i for i in approved_items if i.get("item_type") == "epic"]
    tasks_raw = [i for i in approved_items if i.get("item_type") == "task"]
    subtasks_raw = [i for i in approved_items if i.get("item_type") == "subtask"]

    # Build subtask list per task_id
    subtasks_by_task: dict[str, list[Subtask]] = {}
    for sub in subtasks_raw:
        parent_id = sub.get("parent_id")
        if not parent_id:
            continue
        priority_str = sub.get("priority") or "Medium"
        valid_priorities = [p.value for p in Priority]
        priority = (
            Priority(priority_str)
            if priority_str in valid_priorities
            else Priority.MEDIUM
        )
        subtask = Subtask(
            summary=sub.get("title") or "",
            assignee=sub.get("assignee"),
            deadline=sub.get("deadline"),
            priority=priority,
            context=sub.get("description") or "",
        )
        subtasks_by_task.setdefault(parent_id, []).append(subtask)

    # Build task list per epic_id; orphan_tasks are top-level tasks with no parent epic
    tasks_by_epic: dict[str, list[Task]] = {}
    orphan_tasks: list[Task] = []
    for task in tasks_raw:
        parent_id = task.get("parent_id")
        priority_str = task.get("priority") or "Medium"
        valid_priorities = [p.value for p in Priority]
        priority = (
            Priority(priority_str)
            if priority_str in valid_priorities
            else Priority.MEDIUM
        )
        t = Task(
            summary=task.get("title") or "",
            assignee=task.get("assignee"),
            deadline=task.get("deadline"),
            priority=priority,
            context=task.get("description") or "",
            subtasks=subtasks_by_task.get(task["id"], []),
        )
        if parent_id:
            tasks_by_epic.setdefault(parent_id, []).append(t)
        else:
            orphan_tasks.append(t)

    # Build epics
    epics = []
    for epic in epics_raw:
        epic_tasks = tasks_by_epic.get(epic["id"], [])
        epics.append(Epic(
            summary=epic.get("title") or "",
            description=epic.get("description") or "",
            tasks=epic_tasks,
        ))

    # Include any top-level tasks that have no parent epic
    for orphan_task in orphan_tasks:
        epics.append(Epic(
            summary="Action Items",
            description="Top-level action items without a parent epic",
            tasks=[orphan_task],
        ))

    return MeetingAnalysis(epics=epics)
