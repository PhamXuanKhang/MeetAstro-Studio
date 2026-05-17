"""
Router: /api/v1/meetings/{id}/analyze - analyze transcript.

POST /meetings/{id}/analyze    Start analysis job
GET  /meetings/{id}/analysis   Get analysis result
"""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from src.api.deps import get_supabase
from src.api.schemas.meeting_schemas import AnalysisPatch, AnalysisResponse
from src.api.schemas.task_schemas import JobStatusResponse
from src.db.crud.meeting_crud import (
    get_analysis_result,
    get_meeting,
    get_transcript_segments,
    update_analysis_result,
    update_meeting_status,
)
from supabase import Client

router = APIRouter(prefix="/meetings", tags=["analysis"])


@router.post("/{meeting_id}/analyze", response_model=JobStatusResponse)
async def start_analysis(
    meeting_id: uuid.UUID,
    supabase: Annotated[Client, Depends(get_supabase)],
) -> JobStatusResponse:
    """Start analysis job. Transcript must exist first."""
    meeting = get_meeting(str(meeting_id))
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found.")

    segments = get_transcript_segments(str(meeting_id))
    if not segments:
        raise HTTPException(
            status_code=400, detail="Transcript not found. Run transcription first."
        )

    from src.workers.tasks.analyze_task import analyze_transcript

    task = analyze_transcript.delay(str(meeting_id), transcript_id="")
    update_meeting_status(
        str(meeting_id), status="analyzing"
    )
    return JobStatusResponse(job_id=task.id, state="PENDING")


@router.post("/{meeting_id}/action-items/regenerate", response_model=JobStatusResponse)
async def regenerate_action_items_from_note_endpoint(
    meeting_id: uuid.UUID,
    supabase: Annotated[Client, Depends(get_supabase)],
) -> JobStatusResponse:
    """Regenerate non-synced action items from the current meeting note."""
    meeting = get_meeting(str(meeting_id))
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found.")

    result = get_analysis_result(str(meeting_id))
    if not result:
        raise HTTPException(
            status_code=400,
            detail="Analysis result not found. Run analysis first.",
        )

    from src.workers.tasks.analyze_task import regenerate_action_items_from_note

    task = regenerate_action_items_from_note.delay(str(meeting_id))
    update_meeting_status(str(meeting_id), status="analyzing")
    return JobStatusResponse(job_id=task.id, state="PENDING")


@router.get("/{meeting_id}/analysis", response_model=AnalysisResponse)
async def get_analysis_endpoint(
    meeting_id: uuid.UUID,
    supabase: Annotated[Client, Depends(get_supabase)],
) -> AnalysisResponse:
    """Get analysis result for meeting."""
    result = get_analysis_result(str(meeting_id))
    if not result:
        raise HTTPException(
            status_code=404, detail="Analysis not found. Run analyze first."
        )
    return AnalysisResponse.model_validate(result)


@router.patch("/{meeting_id}/analysis", response_model=AnalysisResponse)
async def patch_analysis_endpoint(
    meeting_id: uuid.UUID,
    payload: AnalysisPatch,
    supabase: Annotated[Client, Depends(get_supabase)],
) -> AnalysisResponse:
    """Update editable meeting-note fields in analysis_results."""
    meeting = get_meeting(str(meeting_id))
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found.")

    try:
        updated = update_analysis_result(
            str(meeting_id),
            summary_text=payload.summary_text,
            key_decisions=payload.key_decisions,
            discussion_points=payload.discussion_points,
            parking_lot=payload.parking_lot,
            action_plan_draft=payload.action_plan_draft,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return AnalysisResponse.model_validate(updated)
