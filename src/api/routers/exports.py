"""
Router: /api/v1/meetings/{id}/export - export results.

GET /meetings/{id}/export/markdown   Markdown string
GET /meetings/{id}/export/json       JSON file
GET /meetings/{id}/export/csv       CSV file (attachment)
"""
import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse, Response

from src.db.crud.meeting_crud import get_analysis_result, get_meeting
from src.modules.exporter import export_csv, export_json, export_markdown
from src.schema import MeetingAnalysis

router = APIRouter(prefix="/meetings", tags=["exports"])


def _get_analysis_or_404(meeting_id: str) -> MeetingAnalysis:
    """Helper to get analysis or raise 404."""
    result = get_analysis_result(meeting_id)
    if not result:
        raise HTTPException(
            status_code=404, detail="Analysis not found. Run analyze first."
        )
    # Column mapping: Supabase uses raw_response, not analysis_json
    return MeetingAnalysis.from_dict(result.get("raw_response", {}))


def _assert_meeting_exists(meeting_id: str) -> None:
    """Helper to check meeting exists."""
    meeting = get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found.")


@router.get("/{meeting_id}/export/markdown", response_class=PlainTextResponse)
async def export_markdown_endpoint(meeting_id: uuid.UUID) -> str:
    """Export result as Markdown."""
    _assert_meeting_exists(str(meeting_id))
    analysis = _get_analysis_or_404(str(meeting_id))
    return export_markdown(analysis)


@router.get("/{meeting_id}/export/json")
async def export_json_endpoint(meeting_id: uuid.UUID) -> Response:
    """Export result as JSON."""
    _assert_meeting_exists(str(meeting_id))
    analysis = _get_analysis_or_404(str(meeting_id))
    content = export_json(analysis)
    return Response(
        content=content,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="meeting_{meeting_id}.json"'
        },
    )


@router.get("/{meeting_id}/export/csv")
async def export_csv_endpoint(meeting_id: uuid.UUID) -> Response:
    """Export result as CSV."""
    _assert_meeting_exists(str(meeting_id))
    analysis = _get_analysis_or_404(str(meeting_id))
    content = export_csv(analysis)
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="meeting_{meeting_id}.csv"'
        },
    )
