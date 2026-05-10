"""
Celery task: push approved review items to Jira.

Input:  meeting_id (str)
Output: {"epic_keys": list, "task_count": int, "subtask_count": int, "is_stub": bool}
"""
from src.config import get_logger
from src.db.crud.meeting_crud import get_analysis_result, update_meeting_status
from src.db.crud.review_crud import list_review_items
from src.services.jira_service import push_analysis_to_jira
from src.workers.celery_app import celery_app

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

    analysis_result = get_analysis_result(meeting_id)
    meeting_analysis = _reconstruct_analysis(items, analysis_result)

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


def _reconstruct_analysis(approved_items, analysis_result):
    """
    Reconstruct MeetingAnalysis from list of approved ReviewItems.

    Uses edited_* fields if user has made edits, otherwise uses original fields.
    """
    from src.schema import Epic, MeetingAnalysis, Priority, Subtask, Task

    epics_map: dict[str, dict] = {}

    for item in approved_items:
        parts = item.get("item_index", "").split(".")
        summary = item.get("edited_summary") or item.get("summary")
        assignee = item.get("edited_assignee") or item.get("assignee")
        deadline = item.get("edited_deadline") or item.get("deadline")
        priority_str = item.get("edited_priority") or item.get("priority") or "Medium"
        valid_priorities = [p.value for p in Priority]
        priority = Priority(priority_str) if priority_str in valid_priorities else Priority.MEDIUM

        if item.get("item_type") == "epic":
            epic_idx = parts[0]
            if epic_idx not in epics_map:
                epics_map[epic_idx] = {
                    "summary": summary,
                    "description": item.get("context") or "",
                    "tasks": {},
                }

        elif item.get("item_type") == "task":
            epic_idx, task_idx = parts[0], parts[1]
            if epic_idx not in epics_map:
                epics_map[epic_idx] = {
                    "summary": f"Epic {epic_idx}", "description": "", "tasks": {}
                }
            epics_map[epic_idx]["tasks"][task_idx] = {
                "summary": summary,
                "assignee": assignee,
                "deadline": deadline,
                "priority": priority,
                "context": item.get("context") or "",
                "subtasks": {},
            }

        elif item.get("item_type") == "subtask":
            epic_idx, task_idx, sub_idx = parts[0], parts[1], parts[2]
            if epic_idx not in epics_map:
                epics_map[epic_idx] = {
                    "summary": f"Epic {epic_idx}", "description": "", "tasks": {}
                }
            if task_idx not in epics_map[epic_idx]["tasks"]:
                epics_map[epic_idx]["tasks"][task_idx] = {
                    "summary": f"Task {task_idx}", "assignee": None,
                    "deadline": None, "priority": Priority.MEDIUM,
                    "context": "", "subtasks": {},
                }
            epics_map[epic_idx]["tasks"][task_idx]["subtasks"][sub_idx] = Subtask(
                summary=summary, assignee=assignee, deadline=deadline,
                priority=priority, context=item.get("context") or "",
            )

    epics = []
    for epic_idx in sorted(epics_map.keys(), key=int):
        epic_data = epics_map[epic_idx]
        tasks = []
        for task_idx in sorted(epic_data["tasks"].keys(), key=int):
            task_data = epic_data["tasks"][task_idx]
            subtasks = [
                task_data["subtasks"][s]
                for s in sorted(task_data["subtasks"].keys(), key=int)
            ]
            tasks.append(Task(
                summary=task_data["summary"],
                assignee=task_data["assignee"],
                deadline=task_data["deadline"],
                priority=task_data["priority"],
                context=task_data["context"],
                subtasks=subtasks,
            ))
        epics.append(Epic(
            summary=epic_data["summary"],
            description=epic_data["description"],
            tasks=tasks,
        ))

    summary_text = analysis_result.get("summary", "") if analysis_result else ""
    return MeetingAnalysis(epics=epics, summary=summary_text)
