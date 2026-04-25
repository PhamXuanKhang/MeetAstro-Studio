"""
Router: /api/v1/meetings/{id}/export - export results.

GET /meetings/{id}/export/markdown   Markdown string
GET /meetings/{id}/export/json       JSON file
GET /meetings/{id}/export/csv        CSV file (attachment)
"""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db
from src.db.crud.meeting_crud import get_analysis_result, get_meeting
from src.modules.exporter import export_csv, export_json, export_markdown
from src.schema import MeetingAnalysis

router = APIRouter(prefix="/meetings", tags=["exports"])


async def _get_analysis_or_404(
    db: AsyncSession, meeting_id: uuid.UUID
) -> MeetingAnalysis:
    """Helper to get analysis or raise 404."""
    result = await get_analysis_result(db, meeting_id)
    if not result:
        raise HTTPException(
            status_code=404, detail="Analysis not found. Run analyze first."
        )
    return MeetingAnalysis.from_dict(result.analysis_json)


@router.get("/{meeting_id}/export/markdown", response_class=PlainTextResponse)
async def export_markdown_endpoint(
    meeting_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> str:
    """Export result as Markdown."""
    await _assert_meeting_exists(db, meeting_id)
    analysis = await _get_analysis_or_404(db, meeting_id)
    return export_markdown(analysis)


@router.get("/{meeting_id}/export/json")
async def export_json_endpoint(
    meeting_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """Export result as JSON."""
    await _assert_meeting_exists(db, meeting_id)
    analysis = await _get_analysis_or_404(db, meeting_id)
    content = export_json(analysis)
    return Response(
        content=content,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="meeting_{meeting_id}.json"'
        },
    )


@router.get("/{meeting_id}/export/csv")
async def export_csv_endpoint(
    meeting_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """Export result as CSV."""
    await _assert_meeting_exists(db, meeting_id)
    analysis = await _get_analysis_or_404(db, meeting_id)
    content = export_csv(analysis)
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="meeting_{meeting_id}.csv"'
        },
    )


async def _assert_meeting_exists(db: AsyncSession, meeting_id: uuid.UUID) -> None:
    """Helper to check meeting exists."""
    meeting = await get_meeting(db, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found.")
