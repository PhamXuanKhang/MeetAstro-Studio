"""
Router: /api/v1/meetings - CRUD meetings and audio upload.

POST /meetings                 Create meeting
GET  /meetings                 List meetings
GET  /meetings/{id}            Get meeting details
DELETE /meetings/{id}          Delete meeting
POST /meetings/{id}/audio      Upload audio -> queue pipeline
"""
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
from src.db.crud.meeting_crud import (
    create_meeting,
    delete_meeting,
    get_meeting,
    list_meetings,
    update_meeting_status,
)

router = APIRouter(prefix="/meetings", tags=["meetings"])

ZERO_UUID = uuid.UUID(int=0)


@router.post("", response_model=MeetingResponse, status_code=status.HTTP_201_CREATED)
async def create_meeting_endpoint(
    payload: MeetingCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MeetingResponse:
    """Create a new meeting record."""
    meeting = await create_meeting(
        db, title=payload.title, user_id=(payload.user_id or ZERO_UUID)
    )
    return MeetingResponse.model_validate(meeting)


@router.get("", response_model=MeetingListResponse)
async def list_meetings_endpoint(
    db: Annotated[AsyncSession, Depends(get_db)],
    status: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user_id: uuid.UUID = Query(default=ZERO_UUID),
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
    Upload audio/video file, normalize to WAV 16kHz mono, and queue pipeline.

    Supported formats:
    - Audio: .mp3, .wav, .m4a, .ogg
    - Video: .mp4, .mkv, .webm (audio track is extracted)

    Returns job_id for polling progress via GET /jobs/{job_id}.
    """
    from src.services.audio_ingestion_service import (
        AudioProcessingError,
        FileTooLarge,
        UnsupportedFileFormat,
        process_upload,
    )

    meeting = await get_meeting(db, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found.")
    if meeting.status not in ("pending", "failed"):
        raise HTTPException(
            status_code=409,
            detail=f"Meeting is in '{meeting.status}' state, cannot re-upload.",
        )

    # ── Validate & process upload ──
    try:
        audio_path, storage_path, duration = process_upload(
            file_stream=file.file,
            filename=file.filename or "upload.wav",
            user_id=meeting.user_id,
            meeting_id=str(meeting_id),
            file_size=file.size,
        )
    except UnsupportedFileFormat as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except FileTooLarge as exc:
        raise HTTPException(status_code=413, detail=str(exc))
    except AudioProcessingError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    # ── Update meeting record ──
    from sqlalchemy import update as sa_update
    from src.db.models import Meeting as MeetingModel

    await db.execute(
        sa_update(MeetingModel)
        .where(MeetingModel.id == meeting_id)
        .values(
            audio_path=audio_path,
            audio_storage_path=storage_path,
            audio_duration_seconds=duration,
        )
    )
    await update_meeting_status(db, meeting_id, status="pending")

    # ── Queue pipeline ──
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
        audio_storage_path=storage_path,
        audio_duration_seconds=duration,
    )
