"""
Request/Response schemas cho Human-in-the-Loop review API.
"""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel


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

    model_config = {"from_attributes": True}


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
