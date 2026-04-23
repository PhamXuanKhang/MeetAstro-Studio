"""
Router: /api/v1/meetings/{id}/analyze — phân tích transcript.

POST /meetings/{id}/analyze    Bắt đầu analysis job
GET  /meetings/{id}/analysis   Lấy kết quả analysis
"""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db
from src.api.schemas.meeting_schemas import AnalysisResponse
from src.api.schemas.task_schemas import JobStatusResponse
from src.db.crud.meeting_crud import (
    get_analysis_result,
    get_meeting,
    get_transcript,
    update_meeting_status,
)

router = APIRouter(prefix="/meetings", tags=["analysis"])


@router.post("/{meeting_id}/analyze", response_model=JobStatusResponse)
async def start_analysis(
    meeting_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JobStatusResponse:
    """Bắt đầu analysis job. Transcript phải tồn tại trước."""
    meeting = await get_meeting(db, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting không tồn tại.")

    transcript = await get_transcript(db, meeting_id)
    if not transcript:
        raise HTTPException(
            status_code=400, detail="Transcript chưa có. Chạy transcription trước."
        )

    from src.workers.tasks.analyze_task import analyze_transcript
    task = analyze_transcript.delay(str(meeting_id), str(transcript.id))
    await update_meeting_status(
        db, meeting_id, status="analyzing", celery_task_id=task.id
    )
    return JobStatusResponse(job_id=task.id, state="PENDING")


@router.get("/{meeting_id}/analysis", response_model=AnalysisResponse)
async def get_analysis_endpoint(
    meeting_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AnalysisResponse:
    """Lấy kết quả analysis của meeting."""
    result = await get_analysis_result(db, meeting_id)
    if not result:
        raise HTTPException(
            status_code=404, detail="Analysis chưa có. Chạy analyze trước."
        )
    return AnalysisResponse.model_validate(result)
