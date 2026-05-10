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

from src.api.deps import get_supabase
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
    update_meeting,
    update_meeting_status,
)
from supabase import Client

router = APIRouter(prefix="/meetings", tags=["meetings"])

ZERO_UUID = "00000000-0000-0000-0000-000000000000"


@router.post("", response_model=MeetingResponse, status_code=status.HTTP_201_CREATED)
async def create_meeting_endpoint(
    payload: MeetingCreate,
    supabase: Annotated[Client, Depends(get_supabase)],
) -> MeetingResponse:
    """Create a new meeting record."""
    meeting = create_meeting(
        title=payload.title,
        user_id=str(payload.user_id or ZERO_UUID),
    )
    return MeetingResponse.model_validate(meeting)


@router.get("", response_model=MeetingListResponse)
async def list_meetings_endpoint(
    supabase: Annotated[Client, Depends(get_supabase)],
    status: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user_id: uuid.UUID = Query(default=None),
) -> MeetingListResponse:
    """Get list of meetings with pagination."""
    items, total = list_meetings(
        user_id=str(user_id or ZERO_UUID),
        status=status,
        page=page,
        page_size=page_size,
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
    supabase: Annotated[Client, Depends(get_supabase)],
) -> MeetingResponse:
    """Get details of a specific meeting."""
    meeting = get_meeting(str(meeting_id))
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found.")
    return MeetingResponse.model_validate(meeting)


@router.delete("/{meeting_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meeting_endpoint(
    meeting_id: uuid.UUID,
    supabase: Annotated[Client, Depends(get_supabase)],
) -> None:
    """Delete meeting and cascade delete all related data."""
    deleted = delete_meeting(str(meeting_id))
    if not deleted:
        raise HTTPException(status_code=404, detail="Meeting not found.")


@router.post("/{meeting_id}/audio", response_model=AudioUploadResponse)
async def upload_audio_endpoint(
    meeting_id: uuid.UUID,
    supabase: Annotated[Client, Depends(get_supabase)],
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

    meeting = get_meeting(str(meeting_id))
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found.")
    if meeting.get("status") not in ("pending", "failed"):
        raise HTTPException(
            status_code=409,
            detail=f"Meeting is in '{meeting.get('status')}' state, cannot re-upload.",
        )

    # Validate & process upload
    try:
        audio_path, storage_path, duration = process_upload(
            file_stream=file.file,
            filename=file.filename or "upload.wav",
            user_id=meeting.get("user_id", ZERO_UUID),
            meeting_id=str(meeting_id),
            file_size=file.size,
        )
    except UnsupportedFileFormat as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except FileTooLarge as exc:
        raise HTTPException(status_code=413, detail=str(exc))
    except AudioProcessingError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    # Update meeting record
    update_meeting(
        str(meeting_id),
        audio_path=audio_path,
        audio_storage_path=storage_path,
        audio_duration_seconds=duration,
    )

    # Queue pipeline
    from src.workers.pipeline import run_pipeline

    task = run_pipeline.delay(
        str(meeting_id), audio_path, diarize=diarize, language=language
    )

    update_meeting_status(
        str(meeting_id),
        status="pending",
        celery_task_id=task.id,
    )

    return AudioUploadResponse(
        meeting_id=meeting_id,
        job_id=task.id,
        audio_storage_path=storage_path,
        audio_duration_seconds=duration,
    )
