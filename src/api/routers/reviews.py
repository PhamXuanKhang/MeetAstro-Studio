"""
Router: Human-in-the-Loop review workflow.

GET    /meetings/{id}/review                 List review items
GET    /meetings/{id}/review/summary         Summary stats
GET    /meetings/{id}/review/{item_id}       Item details
PATCH  /meetings/{id}/review/{item_id}       Edit item
POST   /meetings/{id}/review/{item_id}/approve  Approve item
POST   /meetings/{id}/review/{item_id}/reject   Reject item
POST   /meetings/{id}/review/approve_all     Approve all
"""
import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db
from src.api.schemas.review_schemas import (
    ReviewItemPatch,
    ReviewItemResponse,
    ReviewSummaryResponse,
)
from src.db.crud.meeting_crud import get_meeting
from src.db.crud.review_crud import (
    approve_all_items,
    get_review_item,
    get_review_summary,
    list_review_items,
    set_review_status,
    update_review_item,
)

router = APIRouter(prefix="/meetings", tags=["reviews"])


@router.get("/{meeting_id}/review/summary", response_model=ReviewSummaryResponse)
async def review_summary(
    meeting_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ReviewSummaryResponse:
    """Get summary stats of review items."""
    await _assert_meeting_exists(db, meeting_id)
    summary = await get_review_summary(db, meeting_id)
    return ReviewSummaryResponse(**summary)


@router.get("/{meeting_id}/review", response_model=list[ReviewItemResponse])
async def list_review_items_endpoint(
    meeting_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    status: Optional[str] = None,
    flagged_only: bool = False,
) -> list[ReviewItemResponse]:
    """List review items with flagged items first."""
    await _assert_meeting_exists(db, meeting_id)
    items = await list_review_items(
        db, meeting_id, status=status, flagged_only=flagged_only
    )
    return [ReviewItemResponse.model_validate(i) for i in items]


@router.get("/{meeting_id}/review/{item_id}", response_model=ReviewItemResponse)
async def get_review_item_endpoint(
    meeting_id: uuid.UUID,
    item_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ReviewItemResponse:
    """Get details of a specific review item."""
    item = await _get_item_or_404(db, item_id, meeting_id)
    return ReviewItemResponse.model_validate(item)


@router.patch("/{meeting_id}/review/{item_id}", response_model=ReviewItemResponse)
async def patch_review_item(
    meeting_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: ReviewItemPatch,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ReviewItemResponse:
    """Edit a review item (sets review_status='edited')."""
    await _get_item_or_404(db, item_id, meeting_id)
    updated = await update_review_item(
        db,
        item_id,
        edited_summary=payload.edited_summary,
        edited_assignee=payload.edited_assignee,
        edited_deadline=payload.edited_deadline,
        edited_priority=payload.edited_priority,
    )
    return ReviewItemResponse.model_validate(updated)


@router.post("/{meeting_id}/review/{item_id}/approve", response_model=ReviewItemResponse)
async def approve_item(
    meeting_id: uuid.UUID,
    item_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ReviewItemResponse:
    """Approve a review item."""
    await _get_item_or_404(db, item_id, meeting_id)
    updated = await set_review_status(db, item_id, status="approved")
    return ReviewItemResponse.model_validate(updated)


@router.post("/{meeting_id}/review/{item_id}/reject", response_model=ReviewItemResponse)
async def reject_item(
    meeting_id: uuid.UUID,
    item_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ReviewItemResponse:
    """Reject a review item."""
    await _get_item_or_404(db, item_id, meeting_id)
    updated = await set_review_status(db, item_id, status="rejected")
    return ReviewItemResponse.model_validate(updated)


@router.post("/{meeting_id}/review/approve_all")
async def approve_all_endpoint(
    meeting_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Approve all items that are not rejected."""
    await _assert_meeting_exists(db, meeting_id)
    count = await approve_all_items(db, meeting_id)
    return {"approved_count": count}


async def _assert_meeting_exists(db: AsyncSession, meeting_id: uuid.UUID) -> None:
    """Helper to check meeting exists."""
    meeting = await get_meeting(db, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found.")


async def _get_item_or_404(db: AsyncSession, item_id: uuid.UUID, meeting_id: uuid.UUID):
    """Helper to get review item or raise 404."""
    item = await get_review_item(db, item_id)
    if not item or item.meeting_id != meeting_id:
        raise HTTPException(status_code=404, detail="Review item not found.")
    return item
