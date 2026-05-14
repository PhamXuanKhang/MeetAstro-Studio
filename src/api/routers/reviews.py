"""
Router: Human-in-the-Loop review workflow.

GET    /meetings/{id}/review                 List review items
GET    /meetings/{id}/review/summary         Summary stats
GET    /meetings/{id}/review/{item_id}       Item details
PATCH  /meetings/{id}/review/{item_id}        Edit item
POST   /meetings/{id}/review/{item_id}/approve  Approve item
POST   /meetings/{id}/review/{item_id}/reject   Reject item
POST   /meetings/{id}/review/approve_all     Approve all
"""
import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException

from src.api.deps import get_supabase
from src.api.schemas.review_schemas import (
    ReviewItemCreate,
    ReviewItemPatch,
    ReviewItemResponse,
    ReviewSummaryResponse,
)
from src.db.crud.meeting_crud import get_meeting
from src.db.crud.review_crud import (
    approve_all_items,
    create_manual_action_item,
    get_review_item,
    get_review_summary,
    list_review_items,
    set_review_status,
    update_review_item,
)
from supabase import Client

router = APIRouter(prefix="/meetings", tags=["reviews"])


@router.get("/{meeting_id}/review/summary", response_model=ReviewSummaryResponse)
async def review_summary(
    meeting_id: uuid.UUID,
    supabase: Annotated[Client, Depends(get_supabase)],
) -> ReviewSummaryResponse:
    """Get summary stats of review items."""
    _assert_meeting_exists(meeting_id)
    summary = get_review_summary(str(meeting_id))
    return ReviewSummaryResponse(**summary)


@router.get("/{meeting_id}/review", response_model=list[ReviewItemResponse])
async def list_review_items_endpoint(
    meeting_id: uuid.UUID,
    supabase: Annotated[Client, Depends(get_supabase)],
    status: Optional[str] = None,
    flagged_only: bool = False,
) -> list[ReviewItemResponse]:
    """List review items with flagged items first."""
    _assert_meeting_exists(meeting_id)
    items = list_review_items(str(meeting_id), status=status, flagged_only=flagged_only)
    return [ReviewItemResponse.from_action_item(i) for i in items]


@router.post("/{meeting_id}/review", response_model=ReviewItemResponse)
async def create_review_item_endpoint(
    meeting_id: uuid.UUID,
    payload: ReviewItemCreate,
    supabase: Annotated[Client, Depends(get_supabase)],
) -> ReviewItemResponse:
    """Create a manual task/subtask from Review UI."""
    _assert_meeting_exists(meeting_id)

    if payload.item_type not in {"task", "subtask"}:
        raise HTTPException(status_code=400, detail="Only task and subtask can be created manually.")

    if payload.item_type == "subtask":
        if not payload.parent_id:
            raise HTTPException(status_code=400, detail="Subtask requires parent_id.")
        parent = _get_item_or_404(payload.parent_id, meeting_id)
        if parent.get("item_type") != "task":
            raise HTTPException(status_code=400, detail="Subtask parent must be a task.")

    data = payload.model_dump()
    created = create_manual_action_item(str(meeting_id), data)
    return ReviewItemResponse.from_action_item(created)


@router.get("/{meeting_id}/review/{item_id}", response_model=ReviewItemResponse)
async def get_review_item_endpoint(
    meeting_id: uuid.UUID,
    item_id: uuid.UUID,
    supabase: Annotated[Client, Depends(get_supabase)],
) -> ReviewItemResponse:
    """Get details of a specific review item."""
    item = _get_item_or_404(item_id, meeting_id)
    return ReviewItemResponse.from_action_item(item)


@router.patch("/{meeting_id}/review/{item_id}", response_model=ReviewItemResponse)
async def patch_review_item(
    meeting_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: ReviewItemPatch,
    supabase: Annotated[Client, Depends(get_supabase)],
) -> ReviewItemResponse:
    """Edit a review item (sets review_status='edited')."""
    _get_item_or_404(item_id, meeting_id)
    updated = update_review_item(
        str(item_id),
        edited_summary=payload.edited_summary,
        edited_assignee=payload.edited_assignee,
        edited_deadline=payload.edited_deadline,
        edited_priority=payload.edited_priority,
    )
    return ReviewItemResponse.from_action_item(updated)


@router.post("/{meeting_id}/review/{item_id}/approve", response_model=ReviewItemResponse)
async def approve_item(
    meeting_id: uuid.UUID,
    item_id: uuid.UUID,
    supabase: Annotated[Client, Depends(get_supabase)],
) -> ReviewItemResponse:
    """Approve a review item."""
    _get_item_or_404(item_id, meeting_id)
    updated = set_review_status(str(item_id), status="approved")
    return ReviewItemResponse.from_action_item(updated)


@router.post("/{meeting_id}/review/{item_id}/reject", response_model=ReviewItemResponse)
async def reject_item(
    meeting_id: uuid.UUID,
    item_id: uuid.UUID,
    supabase: Annotated[Client, Depends(get_supabase)],
) -> ReviewItemResponse:
    """Reject a review item."""
    _get_item_or_404(item_id, meeting_id)
    updated = set_review_status(str(item_id), status="rejected")
    return ReviewItemResponse.from_action_item(updated)


@router.post("/{meeting_id}/review/approve_all")
async def approve_all_endpoint(
    meeting_id: uuid.UUID,
    supabase: Annotated[Client, Depends(get_supabase)],
) -> dict:
    """Approve all items that are not rejected."""
    _assert_meeting_exists(meeting_id)
    count = approve_all_items(str(meeting_id))
    return {"approved_count": count}


def _assert_meeting_exists(meeting_id: uuid.UUID) -> None:
    """Helper to check meeting exists."""
    meeting = get_meeting(str(meeting_id))
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found.")


def _get_item_or_404(item_id: uuid.UUID, meeting_id: uuid.UUID):
    """Helper to get review item or raise 404."""
    item = get_review_item(str(item_id))
    if not item or item.get("meeting_id") != str(meeting_id):
        raise HTTPException(status_code=404, detail="Review item not found.")
    return item
