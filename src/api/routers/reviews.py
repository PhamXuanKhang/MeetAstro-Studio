"""
Router: Human-in-the-Loop review workflow.

GET    /meetings/{id}/review                 Danh sách review items
GET    /meetings/{id}/review/summary         Thống kê
GET    /meetings/{id}/review/{item_id}       Chi tiết item
PATCH  /meetings/{id}/review/{item_id}       Chỉnh sửa item
POST   /meetings/{id}/review/{item_id}/approve  Approve item
POST   /meetings/{id}/review/{item_id}/reject   Reject item
POST   /meetings/{id}/review/approve_all    Approve tất cả
"""
import uuid
from typing import Annotated

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
    """Thống kê trạng thái review items."""
    await _assert_meeting_exists(db, meeting_id)
    summary = await get_review_summary(db, meeting_id)
    return ReviewSummaryResponse(**summary)


@router.get("/{meeting_id}/review", response_model=list[ReviewItemResponse])
async def list_review_items_endpoint(
    meeting_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    status: str | None = None,
    flagged_only: bool = False,
) -> list[ReviewItemResponse]:
    """Danh sách review items, flagged items lên đầu."""
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
    """Lấy chi tiết một review item."""
    item = await _get_item_or_404(db, item_id, meeting_id)
    return ReviewItemResponse.model_validate(item)


@router.patch("/{meeting_id}/review/{item_id}", response_model=ReviewItemResponse)
async def patch_review_item(
    meeting_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: ReviewItemPatch,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ReviewItemResponse:
    """Chỉnh sửa một review item (set review_status='edited')."""
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
    """Approve một review item."""
    await _get_item_or_404(db, item_id, meeting_id)
    updated = await set_review_status(db, item_id, status="approved")
    return ReviewItemResponse.model_validate(updated)


@router.post("/{meeting_id}/review/{item_id}/reject", response_model=ReviewItemResponse)
async def reject_item(
    meeting_id: uuid.UUID,
    item_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ReviewItemResponse:
    """Reject một review item."""
    await _get_item_or_404(db, item_id, meeting_id)
    updated = await set_review_status(db, item_id, status="rejected")
    return ReviewItemResponse.model_validate(updated)


@router.post("/{meeting_id}/review/approve_all")
async def approve_all_endpoint(
    meeting_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Approve tất cả items chưa bị rejected."""
    await _assert_meeting_exists(db, meeting_id)
    count = await approve_all_items(db, meeting_id)
    return {"approved_count": count}


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _assert_meeting_exists(db: AsyncSession, meeting_id: uuid.UUID) -> None:
    meeting = await get_meeting(db, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting không tồn tại.")


async def _get_item_or_404(db: AsyncSession, item_id: uuid.UUID, meeting_id: uuid.UUID):
    item = await get_review_item(db, item_id)
    if not item or item.meeting_id != meeting_id:
        raise HTTPException(status_code=404, detail="Review item không tồn tại.")
    return item
