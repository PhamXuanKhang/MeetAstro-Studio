"""
Request/Response schemas cho Human-in-the-Loop review API.
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
    id: UUID
    meeting_id: UUID
    item_type: str
    item_index: str
    summary: str
    assignee: Optional[str] = None
    deadline: Optional[str] = None
    priority: Optional[str] = None
    context: Optional[str] = None
    confidence: float
    is_flagged: bool
    review_status: str
    edited_summary: Optional[str] = None
    edited_assignee: Optional[str] = None
    edited_deadline: Optional[str] = None
    edited_priority: Optional[str] = None
    validation_notes: list[Any] = []
    created_at: datetime
    updated_at: datetime

    @field_validator("id", "meeting_id", mode="before")
    @classmethod
    def _uuid(cls, v: Any) -> UUID:
        return _uuid_from_str(v)

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _dt(cls, v: Any) -> datetime:
        return _datetime_from_str(v)


class ReviewItemPatch(BaseModel):
    """Fields user có thể chỉnh sửa. Chỉ gửi field cần thay đổi."""
    edited_summary: Optional[str] = None
    edited_assignee: Optional[str] = None
    edited_deadline: Optional[str] = None
    edited_priority: Optional[str] = None


class ReviewSummaryResponse(BaseModel):
    total: int
    approved: int
    rejected: int
    flagged: int
    pending: int
