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
from src.db.supabase_client import ConflictError
from supabase import Client

router = APIRouter(prefix="/meetings", tags=["meetings"])

ZERO_UUID = "7f3572eb-aed9-4e7f-a4b1-41ecb03319e9"


@router.post("", response_model=MeetingResponse, status_code=status.HTTP_201_CREATED)
async def create_meeting_endpoint(
    payload: MeetingCreate,
    supabase: Annotated[Client, Depends(get_supabase)],
) -> MeetingResponse:
    """Create a new meeting record."""
    try:
        meeting = create_meeting(
            title=payload.title,
            user_id=str(payload.user_id or ZERO_UUID),
        )
    except ConflictError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Meeting with title '{payload.title}' already exists for this user.",
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
    client_path: str = Form(
        default="",
        description="file:// URI of the original audio on the user's machine",
    ),
    diarize: bool = Form(default=False),
    language: str = Form(default=""),
) -> AudioUploadResponse:
    """
    Upload audio/video file, normalize to WAV 16kHz mono, and queue pipeline.

    The original file stays on the user's machine. Only a temporary VPS copy is
    kept for Whisper processing, and is deleted after transcription completes.

    The DB stores ``audio_storage_path`` as the ``client_path`` (file:// URI),
    which is the user's local path. The ``storage_provider`` field defaults to "local".

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

    # Validate & process upload (saves temp VPS copy for Whisper)
    try:
        vps_temp_path, duration = process_upload(
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

    # client_path is the file:// URI on the user's machine (stored in DB)
    audio_storage_path = client_path if client_path else None

    # Update meeting record
    update_meeting(
        str(meeting_id),
        audio_storage_path=audio_storage_path,
        audio_duration_seconds=int(duration),
    )

    # Queue pipeline (VPS temp path used for Whisper processing)
    from src.workers.pipeline import run_pipeline

    language_code = language.strip() or None
    task = run_pipeline.delay(
        str(meeting_id), vps_temp_path, diarize=diarize, language=language_code
    )

    update_meeting_status(
        str(meeting_id),
        status="pending",
    )

    return AudioUploadResponse(
        meeting_id=meeting_id,
        job_id=task.id,
        audio_storage_path=audio_storage_path,
        audio_duration_seconds=int(duration),
    )
