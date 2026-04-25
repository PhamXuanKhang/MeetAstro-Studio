"""
Router: /api/v1/meetings/{id}/transcribe - manage transcripts.

POST /meetings/{id}/transcribe     Start transcription job
GET  /meetings/{id}/transcript     Get transcript text
PATCH /meetings/{id}/transcript    Edit transcript
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
    """Start transcription job for meeting with existing audio_path."""
    meeting = await get_meeting(db, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found.")
    if not meeting.audio_path:
        raise HTTPException(
            status_code=400, detail="Meeting has no audio. Upload audio first."
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
    """Get saved transcript for meeting."""
    transcript = await get_transcript(db, meeting_id)
    if not transcript:
        raise HTTPException(
            status_code=404, detail="Transcript not found. Run transcription first."
        )
    return TranscriptResponse.model_validate(transcript)


@router.patch("/{meeting_id}/transcript", response_model=TranscriptResponse)
async def patch_transcript(
    meeting_id: uuid.UUID,
    payload: TranscriptPatch,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TranscriptResponse:
    """Allow user to edit transcript before analysis."""
    transcript = await get_transcript(db, meeting_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found.")
    transcript.raw_text = payload.raw_text
    transcript.char_count = len(payload.raw_text)
    await db.flush()
    await db.refresh(transcript)
    return TranscriptResponse.model_validate(transcript)
