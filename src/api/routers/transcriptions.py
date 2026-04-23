"""
Router: /api/v1/meetings/{id}/transcribe — quản lý transcript.

POST /meetings/{id}/transcribe     Bắt đầu transcription job
GET  /meetings/{id}/transcript     Lấy transcript text
PATCH /meetings/{id}/transcript    Chỉnh sửa transcript
"""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db
from src.api.schemas.meeting_schemas import TranscriptPatch, TranscriptResponse
from src.api.schemas.task_schemas import JobStatusResponse
from src.db.crud.meeting_crud import get_meeting, get_transcript, update_meeting_status

router = APIRouter(prefix="/meetings", tags=["transcriptions"])


@router.post("/{meeting_id}/transcribe", response_model=JobStatusResponse)
async def start_transcription(
    meeting_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    diarize: bool = False,
    language: str = "en",
) -> JobStatusResponse:
    """Bắt đầu transcription job cho meeting đã có audio_path."""
    meeting = await get_meeting(db, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting không tồn tại.")
    if not meeting.audio_path:
        raise HTTPException(
            status_code=400, detail="Meeting chưa có audio. Upload audio trước."
        )

    from src.workers.tasks.transcribe_task import transcribe_audio
    task = transcribe_audio.delay(
        str(meeting_id), meeting.audio_path, diarize=diarize, language=language
    )
    await update_meeting_status(
        db, meeting_id, status="transcribing", celery_task_id=task.id
    )
    return JobStatusResponse(job_id=task.id, state="PENDING")


@router.get("/{meeting_id}/transcript", response_model=TranscriptResponse)
async def get_transcript_endpoint(
    meeting_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TranscriptResponse:
    """Lấy transcript đã lưu của meeting."""
    transcript = await get_transcript(db, meeting_id)
    if not transcript:
        raise HTTPException(
            status_code=404, detail="Transcript chưa có. Chạy transcription trước."
        )
    return TranscriptResponse.model_validate(transcript)


@router.patch("/{meeting_id}/transcript", response_model=TranscriptResponse)
async def patch_transcript(
    meeting_id: uuid.UUID,
    payload: TranscriptPatch,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TranscriptResponse:
    """Cho phép user chỉnh sửa transcript trước khi analyze."""
    transcript = await get_transcript(db, meeting_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript không tồn tại.")
    transcript.raw_text = payload.raw_text
    transcript.char_count = len(payload.raw_text)
    await db.flush()
    await db.refresh(transcript)
    return TranscriptResponse.model_validate(transcript)
