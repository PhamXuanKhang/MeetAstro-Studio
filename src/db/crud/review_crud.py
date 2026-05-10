"""
CRUD cho ReviewItem — Human-in-the-Loop workflow via Supabase.

Dùng supabase-py client (SERVICE_ROLE_KEY). Tất cả hàm đồng bộ (sync).
"""
import uuid
from typing import Any, Optional

from src.db import supabase_client as sc


def bulk_create_review_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Tạo nhiều review items cùng lúc sau khi analysis hoàn thành."""
    if not items:
        return []
    client = sc.get_supabase_client()
    result = client.table(sc.TABLE_REVIEW_ITEMS).insert(items).execute()
    return result.data or []


def delete_review_items_for_meeting(meeting_id: str | uuid.UUID) -> int:
    """Xóa tất cả review items cho một meeting. Trả về số rows đã xóa."""
    client = sc.get_supabase_client()
    # Fetch count before delete
    count_result = client.table(sc.TABLE_REVIEW_ITEMS).select(
        "id", count="exact"
    ).eq("meeting_id", str(meeting_id)).execute()
    count = count_result.count or 0
    if count > 0:
        client.table(sc.TABLE_REVIEW_ITEMS).delete().eq("meeting_id", str(meeting_id)).execute()
    return count


def list_review_items(
    meeting_id: str | uuid.UUID,
    *,
    status: Optional[str] = None,
    flagged_only: bool = False,
) -> list[dict[str, Any]]:
    """Lấy review items của meeting, sắp xếp flagged first."""
    client = sc.get_supabase_client()
    meeting_uuid = str(meeting_id)
    query = client.table(sc.TABLE_REVIEW_ITEMS).select("*").eq("meeting_id", meeting_uuid)
    if status:
        query = query.eq("review_status", status)
    if flagged_only:
        query = query.eq("is_flagged", True)
    # Flagged items lên trước, sau đó theo item_index
    query = query.order("is_flagged", ascending=False).order("item_index", ascending=True)
    result = query.execute()
    return result.data or []


def get_review_item(item_id: str | uuid.UUID) -> Optional[dict[str, Any]]:
    """Lấy một review item theo ID."""
    return sc.fetch_one(sc.TABLE_REVIEW_ITEMS, {"id": str(item_id)})


def update_review_item(
    item_id: str | uuid.UUID,
    *,
    edited_summary: Optional[str] = None,
    edited_assignee: Optional[str] = None,
    edited_deadline: Optional[str] = None,
    edited_priority: Optional[str] = None,
) -> dict[str, Any]:
    """Cập nhật edited_* fields và set review_status='edited'."""
    data: dict[str, Any] = {"review_status": "edited"}
    if edited_summary is not None:
        data["edited_summary"] = edited_summary
    if edited_assignee is not None:
        data["edited_assignee"] = edited_assignee
    if edited_deadline is not None:
        data["edited_deadline"] = edited_deadline
    if edited_priority is not None:
        data["edited_priority"] = edited_priority
    return sc.update_by_id(sc.TABLE_REVIEW_ITEMS, str(item_id), data)


def set_review_status(item_id: str | uuid.UUID, *, status: str) -> dict[str, Any]:
    """Set review_status = approved | rejected."""
    return sc.update_by_id(sc.TABLE_REVIEW_ITEMS, str(item_id), {"review_status": status})


def approve_all_items(meeting_id: str | uuid.UUID) -> int:
    """Approve tất cả items chưa bị rejected. Trả về số items đã approve."""
    client = sc.get_supabase_client()
    # Count before
    count_result = client.table(sc.TABLE_REVIEW_ITEMS).select(
        "id", count="exact"
    ).eq("meeting_id", str(meeting_id)).in_("review_status", ["draft", "edited"]).execute()
    count = count_result.count or 0
    if count > 0:
        client.table(sc.TABLE_REVIEW_ITEMS).update(
            {"review_status": "approved"}
        ).eq("meeting_id", str(meeting_id)).in_("review_status", ["draft", "edited"]).execute()
    return count


def get_review_summary(meeting_id: str | uuid.UUID) -> dict[str, int]:
    """Thống kê review status cho một meeting."""
    items = list_review_items(meeting_id)
    total = len(items)
    approved = sum(1 for i in items if i.get("review_status") == "approved")
    rejected = sum(1 for i in items if i.get("review_status") == "rejected")
    flagged = sum(
        1 for i in items
        if i.get("is_flagged") and i.get("review_status") == "draft"
    )
    pending = sum(1 for i in items if i.get("review_status") in ("draft", "edited"))
    return {
        "total": total,
        "approved": approved,
        "rejected": rejected,
        "flagged": flagged,
        "pending": pending,
    }
