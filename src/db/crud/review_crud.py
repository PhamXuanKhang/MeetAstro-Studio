"""
Async CRUD cho ReviewItem — Human-in-the-Loop workflow.

Mỗi hàm nhận AsyncSession từ FastAPI dependency injection.
"""
import uuid
from typing import Optional

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import ReviewItem


async def bulk_create_review_items(
    db: AsyncSession, items: list[dict]
) -> list[ReviewItem]:
    """Tạo nhiều review items cùng lúc sau khi analysis hoàn thành."""
    orm_items = [ReviewItem(**item) for item in items]
    db.add_all(orm_items)
    await db.flush()
    return orm_items


async def delete_review_items_for_meeting(
    db: AsyncSession, meeting_id: uuid.UUID
) -> int:
    """Delete all review items for a meeting. Returns deleted row count."""
    result = await db.execute(
        delete(ReviewItem).where(ReviewItem.meeting_id == meeting_id)
    )
    return result.rowcount or 0  # type: ignore[attr-defined]


async def list_review_items(
    db: AsyncSession,
    meeting_id: uuid.UUID,
    *,
    status: Optional[str] = None,
    flagged_only: bool = False,
) -> list[ReviewItem]:
    """Lấy review items của meeting, sắp xếp flagged first."""
    stmt = select(ReviewItem).where(ReviewItem.meeting_id == meeting_id)
    if status:
        stmt = stmt.where(ReviewItem.review_status == status)
    if flagged_only:
        stmt = stmt.where(ReviewItem.is_flagged.is_(True))
    # Flagged items lên trước
    stmt = stmt.order_by(ReviewItem.is_flagged.desc(), ReviewItem.item_index)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_review_item(
    db: AsyncSession, item_id: uuid.UUID
) -> Optional[ReviewItem]:
    """Lấy một review item theo ID."""
    result = await db.execute(select(ReviewItem).where(ReviewItem.id == item_id))
    return result.scalar_one_or_none()


async def update_review_item(
    db: AsyncSession,
    item_id: uuid.UUID,
    *,
    edited_summary: Optional[str] = None,
    edited_assignee: Optional[str] = None,
    edited_deadline: Optional[str] = None,
    edited_priority: Optional[str] = None,
) -> Optional[ReviewItem]:
    """Cập nhật edited_* fields và set review_status='edited'."""
    values: dict = {"review_status": "edited"}
    if edited_summary is not None:
        values["edited_summary"] = edited_summary
    if edited_assignee is not None:
        values["edited_assignee"] = edited_assignee
    if edited_deadline is not None:
        values["edited_deadline"] = edited_deadline
    if edited_priority is not None:
        values["edited_priority"] = edited_priority
    await db.execute(update(ReviewItem).where(ReviewItem.id == item_id).values(**values))
    return await get_review_item(db, item_id)


async def set_review_status(
    db: AsyncSession, item_id: uuid.UUID, *, status: str
) -> Optional[ReviewItem]:
    """Set review_status = approved | rejected."""
    await db.execute(
        update(ReviewItem)
        .where(ReviewItem.id == item_id)
        .values(review_status=status)
    )
    return await get_review_item(db, item_id)


async def approve_all_items(
    db: AsyncSession, meeting_id: uuid.UUID
) -> int:
    """Approve tất cả items chưa bị rejected. Trả về số items đã approve."""
    result = await db.execute(
        update(ReviewItem)
        .where(
            ReviewItem.meeting_id == meeting_id,
            ReviewItem.review_status.in_(["draft", "edited"]),
        )
        .values(review_status="approved")
    )
    return result.rowcount or 0  # type: ignore[attr-defined]


async def get_review_summary(
    db: AsyncSession, meeting_id: uuid.UUID
) -> dict:
    """Thống kê review status cho một meeting."""
    items = await list_review_items(db, meeting_id)
    total = len(items)
    approved = sum(1 for i in items if i.review_status == "approved")
    rejected = sum(1 for i in items if i.review_status == "rejected")
    flagged = sum(1 for i in items if i.is_flagged and i.review_status == "draft")
    pending = sum(1 for i in items if i.review_status in ("draft", "edited"))
    return {
        "total": total,
        "approved": approved,
        "rejected": rejected,
        "flagged": flagged,
        "pending": pending,
    }
