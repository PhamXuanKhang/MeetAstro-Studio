"""
Router: /api/v1/meetings/{id}/jira - push to Jira.

POST /meetings/{id}/jira/push      Push approved items to Jira
GET  /meetings/{id}/jira/status    Status of latest push
"""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db
from src.api.schemas.task_schemas import JiraPushResponse, JobStatusResponse
from src.db.crud.meeting_crud import get_meeting
from src.db.crud.review_crud import get_review_summary

router = APIRouter(prefix="/meetings", tags=["jira"])


@router.post("/{meeting_id}/jira/push", response_model=JiraPushResponse)
async def push_to_jira(
    meeting_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JiraPushResponse:
    """
    Push approved review items to Jira.

    Requires all items to be in approved or rejected state (no pending items).
    """
    meeting = await get_meeting(db, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found.")

    summary = await get_review_summary(db, meeting_id)
    if summary["pending"] > 0:
        raise HTTPException(
            status_code=409,
            detail=(
                f"There are {summary['pending']} items pending review. "
                "Approve or reject all items before pushing to Jira."
            ),
        )
    if summary["approved"] == 0:
        raise HTTPException(
            status_code=400, detail="No items have been approved."
        )

    from src.workers.tasks.jira_push_task import push_to_jira as push_task
    task = push_task.delay(str(meeting_id))
    return JiraPushResponse(
        job_id=task.id,
        message=f"Jira push queued. Track at /jobs/{task.id}.",
    )


@router.get("/{meeting_id}/jira/status", response_model=JobStatusResponse)
async def jira_push_status(
    meeting_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JobStatusResponse:
    """Get status of latest Jira push for meeting."""
    meeting = await get_meeting(db, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found.")

    if meeting.status == "pushed":
        return JobStatusResponse(job_id=meeting.celery_task_id or "", state="SUCCESS")
    if meeting.status == "failed" and meeting.error_message:
        return JobStatusResponse(
            job_id=meeting.celery_task_id or "",
            state="FAILURE",
            error=meeting.error_message,
        )
    return JobStatusResponse(
        job_id=meeting.celery_task_id or "",
        state="PENDING" if meeting.status != "approved" else "STARTED",
    )
