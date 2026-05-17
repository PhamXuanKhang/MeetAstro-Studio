"""
CRUD cho ReviewItem — Human-in-the-Loop workflow via Supabase.

Dùng supabase-py client (SERVICE_ROLE_KEY). Tất cả hàm đồng bộ (sync).

Thực tế lưu trong bảng `action_items` của Supabase ( không có bảng `review_items` ).
Field mapping:
  - item_type      → item_type       (epic | task | subtask)
  - is_flagged     → is_selected     (inverted: flagged=False → selected=True)
  - item_index     → (removed — dùng id/order để sắp xếp)
  - edited_*       → (removed — user edit ghi đè trực tiếp vào summary/assignee/deadline/priority)
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from src.db import supabase_client as sc


def bulk_create_review_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Tạo nhiều review items cùng lúc sau khi analysis hoàn thành."""
    if not items:
        return []
    client = sc.get_supabase_client()
    result = client.table(sc.TABLE_ACTION_ITEMS).insert(items).execute()
    return result.data or []


def delete_review_items_for_meeting(meeting_id: str | uuid.UUID) -> int:
    """Xóa tất cả review items cho một meeting. Trả về số rows đã xóa."""
    client = sc.get_supabase_client()
    count_result = client.table(sc.TABLE_ACTION_ITEMS).select(
        "id", count="exact"
    ).eq("meeting_id", str(meeting_id)).execute()
    count = count_result.count or 0
    if count > 0:
        client.table(sc.TABLE_ACTION_ITEMS).delete().eq("meeting_id", str(meeting_id)).execute()
    return count


def delete_non_synced_review_items_for_meeting(meeting_id: str | uuid.UUID) -> int:
    """Delete all action items that have not been synced to Jira."""
    client = sc.get_supabase_client()
    meeting_uuid = str(meeting_id)
    count_result = (
        client.table(sc.TABLE_ACTION_ITEMS)
        .select("id", count="exact")
        .eq("meeting_id", meeting_uuid)
        .neq("sync_status", "synced")
        .execute()
    )
    count = count_result.count or 0
    if count > 0:
        (
            client.table(sc.TABLE_ACTION_ITEMS)
            .delete()
            .eq("meeting_id", meeting_uuid)
            .neq("sync_status", "synced")
            .execute()
        )
    return count


def delete_non_synced_review_items_except(
    meeting_id: str | uuid.UUID,
    *,
    exclude_ids: set[str],
) -> int:
    """Delete non-synced action items, preserving explicitly referenced rows."""
    if not exclude_ids:
        return delete_non_synced_review_items_for_meeting(meeting_id)

    client = sc.get_supabase_client()
    meeting_uuid = str(meeting_id)
    result = (
        client.table(sc.TABLE_ACTION_ITEMS)
        .select("id")
        .eq("meeting_id", meeting_uuid)
        .neq("sync_status", "synced")
        .execute()
    )
    rows = result.data or []
    ids_to_delete = [
        str(row["id"])
        for row in rows
        if row.get("id") and str(row["id"]) not in exclude_ids
    ]
    for item_id in ids_to_delete:
        client.table(sc.TABLE_ACTION_ITEMS).delete().eq("id", item_id).execute()
    return len(ids_to_delete)


def list_synced_review_items(meeting_id: str | uuid.UUID) -> list[dict[str, Any]]:
    """Return action items already synced to Jira for dedupe and continuity."""
    client = sc.get_supabase_client()
    result = (
        client.table(sc.TABLE_ACTION_ITEMS)
        .select("*")
        .eq("meeting_id", str(meeting_id))
        .eq("sync_status", "synced")
        .order("created_at", desc=False)
        .execute()
    )
    return result.data or []


def list_work_status_candidates_for_meeting(
    meeting_id: str | uuid.UUID,
    *,
    meeting_limit: int = 12,
    item_limit: int = 80,
) -> list[dict[str, Any]]:
    """Return recent open task/subtask rows for the same meeting owner."""
    client = sc.get_supabase_client()
    meeting = sc.fetch_one(sc.TABLE_MEETINGS, {"id": str(meeting_id)})
    if not meeting or not meeting.get("user_id"):
        return []

    meetings_result = (
        client.table(sc.TABLE_MEETINGS)
        .select("id")
        .eq("user_id", str(meeting["user_id"]))
        .order("updated_at", desc=True)
        .limit(meeting_limit)
        .execute()
    )
    meeting_ids = [str(row["id"]) for row in (meetings_result.data or []) if row.get("id")]
    if not meeting_ids:
        return []

    items_result = (
        client.table(sc.TABLE_ACTION_ITEMS)
        .select("*")
        .in_("meeting_id", meeting_ids)
        .in_("item_type", ["task", "subtask"])
        .order("updated_at", desc=True)
        .limit(item_limit)
        .execute()
    )
    rows = items_result.data or []
    open_rows = [
        row for row in rows
        if (row.get("work_status") or "todo") not in {"done", "cancelled"}
    ]
    return open_rows[:item_limit]


def update_review_item_parent(
    item_id: str | uuid.UUID,
    parent_id: str | uuid.UUID,
) -> dict[str, Any]:
    """Patch parent_id after bulk insert when parent rows are generated together."""
    return sc.update_by_id(
        sc.TABLE_ACTION_ITEMS,
        str(item_id),
        {"parent_id": str(parent_id)},
    )


def list_review_items(
    meeting_id: str | uuid.UUID,
    *,
    status: Optional[str] = None,
    flagged_only: bool = False,
) -> list[dict[str, Any]]:
    """
    Lấy review items của meeting.

    - flagged_only=True  → is_selected=True  (low-confidence items cần user xem lại)
    - Sắp xếp: selected (flagged) items lên trước, sau đó theo created_at.
    """
    client = sc.get_supabase_client()
    meeting_uuid = str(meeting_id)
    query = client.table(sc.TABLE_ACTION_ITEMS).select("*").eq("meeting_id", meeting_uuid)
    if status:
        query = query.eq("review_status", status)
    if flagged_only:
        query = query.eq("is_selected", True)
    query = query.order("is_selected", desc=False).order("created_at", desc=True)
    result = query.execute()
    return result.data or []


def get_review_item(item_id: str | uuid.UUID) -> Optional[dict[str, Any]]:
    """Lấy một review item theo ID."""
    return sc.fetch_one(sc.TABLE_ACTION_ITEMS, {"id": str(item_id)})


def create_manual_action_item(meeting_id: str | uuid.UUID, data: dict[str, Any]) -> dict[str, Any]:
    """Tạo action item thủ công từ Review UI."""
    payload = {
        "meeting_id": str(meeting_id),
        "parent_id": str(data["parent_id"]) if data.get("parent_id") else None,
        "item_type": data.get("item_type", "task"),
        "title": data.get("title"),
        "description": data.get("description") or "",
        "assignee": data.get("assignee") or None,
        "deadline": _sanitize_for_db(data.get("deadline")),
        "priority": data.get("priority") or "medium",
        "context": data.get("context") or "Manual item",
        "confidence_score": data.get("confidence_score", 1.0),
        "review_status": data.get("review_status", "approved"),
        "is_selected": data.get("is_selected", True),
        "sync_status": data.get("sync_status", "pending"),
    }
    client = sc.get_supabase_client()
    result = client.table(sc.TABLE_ACTION_ITEMS).insert(payload).execute()
    return result.data[0] if result.data else payload


def update_review_item_work_status(
    item_id: str | uuid.UUID,
    *,
    work_status: str,
    note: Optional[str] = None,
) -> dict[str, Any]:
    """Update actual work progress after human approval."""
    data: dict[str, Any] = {
        "work_status": work_status,
        "work_status_updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if note is not None:
        data["work_status_note"] = note
    return sc.update_by_id(sc.TABLE_ACTION_ITEMS, str(item_id), data)


def _sanitize_for_db(value: str | None) -> str | None:
    """Convert 'null' string to None to prevent PostgreSQL date parsing errors."""
    if value is None or value == "" or value.lower() == "null":
        return None
    return value


def update_review_item(
    item_id: str | uuid.UUID,
    *,
    edited_summary: Optional[str] = None,
    edited_assignee: Optional[str] = None,
    edited_deadline: Optional[str] = None,
    edited_priority: Optional[str] = None,
) -> dict[str, Any]:
    """
    Cập nhật item — ghi đè trực tiếp vào summary/assignee/deadline/priority.

    Không có edited_* columns trong action_items, nên ghi đè luôn giá trị gốc.
    review_status được set thành 'edited' để đánh dấu user đã chỉnh sửa.
    """
    data: dict[str, Any] = {"review_status": "edited"}
    if edited_summary is not None:
        data["title"] = edited_summary
    if edited_assignee is not None:
        data["assignee"] = edited_assignee
    if edited_deadline is not None:
        data["deadline"] = _sanitize_for_db(edited_deadline)
    if edited_priority is not None:
        data["priority"] = edited_priority
    return sc.update_by_id(sc.TABLE_ACTION_ITEMS, str(item_id), data)


def set_review_status(item_id: str | uuid.UUID, *, status: str) -> dict[str, Any]:
    """Set review_status = approved | rejected."""
    return sc.update_by_id(sc.TABLE_ACTION_ITEMS, str(item_id), {"review_status": status})


def update_action_item_sync(
    item_id: str | uuid.UUID,
    *,
    sync_status: str,
    sync_error: Optional[str] = None,
    jira_issue_key: Optional[str] = None,
    jira_issue_url: Optional[str] = None,
) -> dict[str, Any]:
    """Update Jira sync metadata for one action item."""
    data: dict[str, Any] = {"sync_status": sync_status}
    if sync_error is not None:
        data["sync_error"] = sync_error
    if jira_issue_key is not None:
        data["jira_issue_key"] = jira_issue_key
    if jira_issue_url is not None:
        data["jira_issue_url"] = jira_issue_url
    return sc.update_by_id(sc.TABLE_ACTION_ITEMS, str(item_id), data)


def approve_all_items(meeting_id: str | uuid.UUID) -> int:
    """Approve tất cả items chưa bị rejected. Trả về số items đã approve."""
    client = sc.get_supabase_client()
    count_result = client.table(sc.TABLE_ACTION_ITEMS).select(
        "id", count="exact"
    ).eq("meeting_id", str(meeting_id)).in_("review_status", ["draft", "edited"]).execute()
    count = count_result.count or 0
    if count > 0:
        client.table(sc.TABLE_ACTION_ITEMS).update(
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
        if i.get("is_selected") and i.get("review_status") == "draft"
    )
    pending = sum(1 for i in items if i.get("review_status") in ("draft", "edited"))
    return {
        "total": total,
        "approved": approved,
        "rejected": rejected,
        "flagged": flagged,
        "pending": pending,
    }
