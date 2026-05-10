"""
Request/Response Pydantic schemas cho meetings API.

Tách biệt với src/schema.py để tránh ô nhiễm domain models.
"""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


def _uuid_from_str(v: Any) -> UUID:
    """Convert string or UUID to UUID."""
    if isinstance(v, UUID):
        return v
    if isinstance(v, str):
        return UUID(v)
    raise ValueError(f"Cannot convert {v!r} to UUID")


def _datetime_from_str(v: Any) -> datetime:
    """Convert ISO string or datetime to datetime."""
    if isinstance(v, datetime):
        return v
    if isinstance(v, str):
        return datetime.fromisoformat(v.replace("Z", "+00:00"))
    raise ValueError(f"Cannot convert {v!r} to datetime")


class MeetingCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    user_id: Optional[UUID] = None


class MeetingResponse(BaseModel):
    id: UUID
    title: str
    audio_path: Optional[str] = None
    audio_storage_path: Optional[str] = None
    audio_duration_seconds: Optional[float] = None
    status: str
    user_id: UUID
    celery_task_id: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @field_validator("id", "user_id", mode="before")
    @classmethod
    def _uuid(cls, v: Any) -> UUID:
        return _uuid_from_str(v)

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _dt(cls, v: Any) -> datetime:
        return _datetime_from_str(v)


class MeetingListResponse(BaseModel):
    items: list[MeetingResponse]
    total: int
    page: int
    page_size: int


class TranscriptResponse(BaseModel):
    id: UUID
    meeting_id: UUID
    raw_text: str
    diarized_text: Optional[str] = None
    language: str
    char_count: Optional[int] = None
    created_at: datetime

    @field_validator("id", "meeting_id", mode="before")
    @classmethod
    def _uuid(cls, v: Any) -> UUID:
        return _uuid_from_str(v)

    @field_validator("created_at", mode="before")
    @classmethod
    def _dt(cls, v: Any) -> datetime:
        return _datetime_from_str(v)


class TranscriptPatch(BaseModel):
    raw_text: str = Field(..., min_length=1)


class AnalysisResponse(BaseModel):
    id: UUID
    meeting_id: UUID
    analysis_json: dict[str, Any]
    summary: Optional[str] = None
    overall_confidence: Optional[float] = None
    validation_metrics: Optional[dict[str, Any]] = None
    created_at: datetime

    @field_validator("id", "meeting_id", mode="before")
    @classmethod
    def _uuid(cls, v: Any) -> UUID:
        return _uuid_from_str(v)

    @field_validator("created_at", mode="before")
    @classmethod
    def _dt(cls, v: Any) -> datetime:
        return _datetime_from_str(v)


class AudioUploadResponse(BaseModel):
    meeting_id: UUID
    job_id: str
    audio_storage_path: Optional[str] = None
    audio_duration_seconds: Optional[float] = None
    status: str = "queued"
    message: str = "Pipeline đã được queue. Dùng /jobs/{job_id} để theo dõi tiến trình."
