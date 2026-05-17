"""
Request/Response schemas cho Human-in-the-Loop review API.

Thực tế dùng bảng `action_items` trong Supabase.
Field mapping (DB → API response):
  - title              → summary
  - description        → context
  - is_selected        → is_flagged  (inverted)
  - parent_id          → parent_id
  - review_status      → review_status (draft | edited | approved | rejected)
  - sync_status        → sync_status (pending | synced | failed)
  - jira_issue_key     → jira_issue_key
  - jira_issue_url     → jira_issue_url
  - confidence_score    → confidence_score
"""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, field_validator


def _uuid_from_str(v: Any) -> UUID:
    if isinstance(v, UUID):
        return v
    if isinstance(v, str):
        return UUID(v)
    raise ValueError(f"Cannot convert {v!r} to UUID")


def _datetime_from_str(v: Any) -> datetime:
    if isinstance(v, datetime):
        return v
    if isinstance(v, str):
        return datetime.fromisoformat(v.replace("Z", "+00:00"))
    raise ValueError(f"Cannot convert {v!r} to datetime")


class ReviewItemResponse(BaseModel):
    """API response schema — mirrors action_items columns with renamed fields."""
    id: UUID
    meeting_id: UUID
    parent_id: Optional[UUID] = None
    item_type: str
    summary: str  # maps from action_items.title
    description: Optional[str] = None  # maps from action_items.description
    assignee: Optional[str] = None
    deadline: Optional[str] = None
    priority: Optional[str] = None
    context: Optional[str] = None  # alias for description
    confidence_score: float
    is_flagged: bool  # maps from action_items.is_selected (inverted)
    review_status: str
    sync_status: Optional[str] = None
    jira_issue_key: Optional[str] = None
    jira_issue_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @field_validator("id", "meeting_id", "parent_id", mode="before")
    @classmethod
    def _uuid(cls, v: Any) -> Optional[UUID]:
        if v is None:
            return None
        if isinstance(v, UUID):
            return v
        if isinstance(v, str):
            return UUID(v)
        raise ValueError(f"Cannot convert {v!r} to UUID")

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _dt(cls, v: Any) -> datetime:
        return _datetime_from_str(v)

    @field_validator("is_flagged", mode="before")
    @classmethod
    def _is_flagged(cls, v: Any) -> bool:
        # action_items.is_selected = True means low-confidence (flagged)
        # review_schemas.is_flagged = True means flagged for review
        return bool(v)

    @field_validator("context", mode="before")
    @classmethod
    def _context(cls, v: Any, info) -> Optional[str]:
        # If context not provided but description is, use description
        if v is None:
            # description was already parsed at this point; we need to reference it
            # but Pydantic doesn't let us easily cross-field in a before validator.
            # Instead, we handle this in model_construct or a computed field.
            return None
        return v

    @classmethod
    def from_action_item(cls, row: dict[str, Any]) -> "ReviewItemResponse":
        """
        Convert a raw action_items row dict to ReviewItemResponse.

        Handles the field renames:
          - title → summary
          - description → context
          - is_selected → is_flagged (inverted)
        """
        return cls(
            id=_uuid_from_str(row["id"]),
            meeting_id=_uuid_from_str(row["meeting_id"]),
            parent_id=_uuid_from_str(row["parent_id"]) if row.get("parent_id") else None,
            item_type=row.get("item_type", "task"),
            summary=row.get("title") or "",
            description=row.get("description"),
            context=row.get("description"),  # same as description
            assignee=row.get("assignee"),
            deadline=row.get("deadline"),
            priority=row.get("priority"),
            confidence_score=float(row.get("confidence_score") or 0.0),
            is_flagged=bool(row.get("is_selected")),  # inverted: selected = flagged
            review_status=row.get("review_status", "draft"),
            sync_status=row.get("sync_status"),
            jira_issue_key=row.get("jira_issue_key"),
            jira_issue_url=row.get("jira_issue_url"),
            created_at=_datetime_from_str(row.get("created_at")),
            updated_at=_datetime_from_str(row.get("updated_at")),
        )


class ReviewItemPatch(BaseModel):
    """
    Fields user có thể chỉnh sửa.
    Ghi đè trực tiếp vào title/assignee/deadline/priority trong action_items.
    """
    edited_summary: Optional[str] = None
    edited_assignee: Optional[str] = None
    edited_deadline: Optional[str] = None
    edited_priority: Optional[str] = None


class ReviewItemCreate(BaseModel):
    """Payload tạo action item thủ công từ Review UI."""
    parent_id: Optional[UUID] = None
    item_type: str = "task"
    title: str
    description: Optional[str] = None
    assignee: Optional[str] = None
    deadline: Optional[str] = None
    priority: Optional[str] = "medium"
    context: Optional[str] = "Manual item"
    confidence_score: float = 1.0
    review_status: str = "approved"
    is_selected: bool = True
    sync_status: str = "pending"


class ReviewSummaryResponse(BaseModel):
    total: int
    approved: int
    rejected: int
    flagged: int
    pending: int
