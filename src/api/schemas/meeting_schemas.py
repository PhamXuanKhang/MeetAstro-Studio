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


class TranscriptSegmentResponse(BaseModel):
    """Single transcript segment."""

    id: UUID
    meeting_id: UUID
    speaker: Optional[str] = None
    start_time: float
    end_time: float
    content: str

    @field_validator("id", "meeting_id", mode="before")
    @classmethod
    def _uuid(cls, v: Any) -> UUID:
        return _uuid_from_str(v)


class TranscriptResponse(BaseModel):
    """Transcript reassembled from segments, with raw segment data."""

    meeting_id: UUID
    text: str  # reassembled full text
    segments: list[TranscriptSegmentResponse]
    char_count: int

    @field_validator("meeting_id", mode="before")
    @classmethod
    def _uuid(cls, v: Any) -> UUID:
        return _uuid_from_str(v)


class TranscriptPatch(BaseModel):
    """Patch request for editing transcript segments."""
    segments: list[dict[str, Any]] = Field(..., min_length=1)


class AnalysisResponse(BaseModel):
    """Response model for analysis_results table."""

    id: UUID
    meeting_id: UUID
    # Column mapping: Supabase uses raw_response, not analysis_json
    raw_response: Optional[dict[str, Any]] = None
    summary_text: Optional[str] = None
    key_decisions: Optional[dict[str, Any]] = None
    parking_lot: Optional[dict[str, Any]] = None
    ai_model: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
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
