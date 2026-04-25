"""
Router: /api/v1/meetings - CRUD meetings and audio upload.

POST /meetings                 Create meeting
GET  /meetings                 List meetings
GET  /meetings/{id}            Get meeting details
DELETE /meetings/{id}          Delete meeting
POST /meetings/{id}/audio      Upload audio -> queue pipeline
"""
import datetime as dt
import os
import shutil
import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db
from src.api.schemas.meeting_schemas import (
    AudioUploadResponse,
    MeetingCreate,
    MeetingListResponse,
    MeetingResponse,
)
from src.config import get_settings
from src.db.crud.meeting_crud import (
    create_meeting,
    delete_meeting,
    get_meeting,
    list_meetings,
    update_meeting_status,
)

router = APIRouter(prefix="/meetings", tags=["meetings"])


@router.post("", response_model=MeetingResponse, status_code=status.HTTP_201_CREATED)
async def create_meeting_endpoint(
    payload: MeetingCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MeetingResponse:
    """Create a new meeting record."""
    meeting = await create_meeting(
        db, title=payload.title, user_id=payload.user_id
    )
    return MeetingResponse.model_validate(meeting)


@router.get("", response_model=MeetingListResponse)
async def list_meetings_endpoint(
    db: Annotated[AsyncSession, Depends(get_db)],
    status: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user_id: str = Query(default="default_user"),
) -> MeetingListResponse:
    """Get list of meetings with pagination."""
    items, total = await list_meetings(
        db, user_id=user_id, status=status, page=page, page_size=page_size
    )
    return MeetingListResponse(
        items=[MeetingResponse.model_validate(m) for m in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{meeting_id}", response_model=MeetingResponse)
async def get_meeting_endpoint(
    meeting_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MeetingResponse:
    """Get details of a specific meeting."""
    meeting = await get_meeting(db, meeting_id, load_relations=True)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found.")
    return MeetingResponse.model_validate(meeting)


@router.delete("/{meeting_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meeting_endpoint(
    meeting_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete meeting and cascade delete all related data."""
    deleted = await delete_meeting(db, meeting_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Meeting not found.")


@router.post("/{meeting_id}/audio", response_model=AudioUploadResponse)
async def upload_audio_endpoint(
    meeting_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
    diarize: bool = Form(default=False),
    language: str = Form(default="en"),
) -> AudioUploadResponse:
    """
    Upload audio file and queue transcribe -> analyze pipeline.

    Returns job_id for polling progress via GET /jobs/{job_id}.
    """
    meeting = await get_meeting(db, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found.")
    if meeting.status not in ("pending", "failed"):
        raise HTTPException(
            status_code=409,
            detail=f"Meeting is in '{meeting.status}' state, cannot re-upload.",
        )

    settings = get_settings()
    audio_dir = settings.audio_output_dir
    os.makedirs(audio_dir, exist_ok=True)

    timestamp = dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    ext = os.path.splitext(file.filename or "audio.wav")[1] or ".wav"
    audio_path = os.path.join(audio_dir, f"upload_{timestamp}_{meeting_id}{ext}")

    with open(audio_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    await update_meeting_status(db, meeting_id, status="pending")
    from sqlalchemy import update as sa_update

    from src.db.models import Meeting as MeetingModel
    await db.execute(
        sa_update(MeetingModel)
        .where(MeetingModel.id == meeting_id)
        .values(audio_path=audio_path)
    )

    from src.workers.pipeline import run_pipeline
    task = run_pipeline.delay(
        str(meeting_id), audio_path, diarize=diarize, language=language
    )

    await update_meeting_status(
        db, meeting_id, status="pending", celery_task_id=task.id
    )

    return AudioUploadResponse(
        meeting_id=meeting_id,
        job_id=task.id,
    )
