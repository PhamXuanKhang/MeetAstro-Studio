"""
Celery task: push approved review items lên Jira.

Input:  meeting_id (str)
Output: {"epic_keys": list, "task_count": int, "subtask_count": int, "is_stub": bool}
"""
from __future__ import annotations

import asyncio
import uuid

from src.config import get_logger
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
    """Push approved items lên Jira và update meeting status."""
    return asyncio.run(_push_async(self, meeting_id))


async def _push_async(task, meeting_id: str) -> dict:
    from src.db.crud.meeting_crud import get_analysis_result, update_meeting_status
    from src.db.crud.review_crud import list_review_items
    from src.db.session import get_session_factory
    from src.services.jira_service import push_analysis_to_jira

    session_factory = get_session_factory()

    meeting_uuid = uuid.UUID(meeting_id)

    async with session_factory() as db:
        items = await list_review_items(db, meeting_uuid, status="approved")
        analysis_result = await get_analysis_result(db, meeting_uuid)

        if not items:
            raise ValueError("Không có approved items để push.")

        # Reconstruct MeetingAnalysis từ approved review_items
        meeting_analysis = _reconstruct_analysis(items, analysis_result)

    try:
        logger.info(f"[jira_push_task] Bắt đầu push Jira cho meeting {meeting_id}")
        push_result = push_analysis_to_jira(meeting_analysis)
    except Exception as exc:
        async with session_factory() as db:
            await update_meeting_status(
                db, meeting_uuid, status="failed", error_message=str(exc)
            )
            await db.commit()
        raise task.retry(exc=exc)

    async with session_factory() as db:
        await update_meeting_status(db, meeting_uuid, status="pushed")
        await db.commit()

    logger.info(
        f"[jira_push_task] Xong: epic_keys={push_result.epic_keys} "
        f"tasks={push_result.task_count} subtasks={push_result.subtask_count}"
    )
    return {
        "epic_keys": push_result.epic_keys,
        "task_count": push_result.task_count,
        "subtask_count": push_result.subtask_count,
        "is_stub": push_result.is_stub,
    }


def _reconstruct_analysis(approved_items, analysis_result):
    """
    Tái tạo MeetingAnalysis từ danh sách approved ReviewItem.

    Dùng edited_* fields nếu user đã chỉnh sửa, ngược lại dùng original fields.
    """
    from src.schema import Epic, MeetingAnalysis, Priority, Subtask, Task

    # Group items theo item_index hierarchy
    epics_map: dict[str, dict] = {}

    for item in approved_items:
        parts = item.item_index.split(".")
        # Lấy giá trị effective (edited nếu có, original nếu không)
        summary = item.edited_summary or item.summary
        assignee = item.edited_assignee or item.assignee
        deadline = item.edited_deadline or item.deadline
        priority_str = item.edited_priority or item.priority or "Medium"
        valid_priorities = [p.value for p in Priority]
        priority = Priority(priority_str) if priority_str in valid_priorities else Priority.MEDIUM

        if item.item_type == "epic":
            epic_idx = parts[0]
            if epic_idx not in epics_map:
                epics_map[epic_idx] = {
                    "summary": summary,
                    "description": item.context or "",
                    "tasks": {},
                }

        elif item.item_type == "task":
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
                "context": item.context or "",
                "subtasks": {},
            }

        elif item.item_type == "subtask":
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
                priority=priority, context=item.context or "",
            )

    # Xây dựng MeetingAnalysis
    epics = []
    for epic_idx in sorted(epics_map.keys()):
        epic_data = epics_map[epic_idx]
        tasks = []
        for task_idx in sorted(epic_data["tasks"].keys()):
            task_data = epic_data["tasks"][task_idx]
            subtasks = [
                task_data["subtasks"][s]
                for s in sorted(task_data["subtasks"].keys())
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

    summary_text = ""
    if analysis_result and analysis_result.summary:
        summary_text = analysis_result.summary

    return MeetingAnalysis(epics=epics, summary=summary_text)
