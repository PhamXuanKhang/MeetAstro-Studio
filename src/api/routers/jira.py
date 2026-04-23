"""
Router: /api/v1/meetings/{id}/jira — push sang Jira.

POST /meetings/{id}/jira/push      Push approved items → Jira
GET  /meetings/{id}/jira/status    Trạng thái push gần nhất
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
    Push các approved review items lên Jira.
    Yêu cầu tất cả items phải ở trạng thái approved hoặc rejected (không còn pending).
    """
    meeting = await get_meeting(db, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting không tồn tại.")

    summary = await get_review_summary(db, meeting_id)
    if summary["pending"] > 0:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Còn {summary['pending']} items chưa review. "
                "Approve hoặc reject tất cả trước khi push Jira."
            ),
        )
    if summary["approved"] == 0:
        raise HTTPException(
            status_code=400, detail="Không có item nào được approve."
        )

    from src.workers.tasks.jira_push_task import push_to_jira as push_task
    task = push_task.delay(str(meeting_id))
    return JiraPushResponse(
        job_id=task.id,
        message=f"Đã queue Jira push. Theo dõi tại /jobs/{task.id}.",
    )


@router.get("/{meeting_id}/jira/status", response_model=JobStatusResponse)
async def jira_push_status(
    meeting_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JobStatusResponse:
    """Trạng thái Jira push gần nhất của meeting."""
    meeting = await get_meeting(db, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting không tồn tại.")

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
