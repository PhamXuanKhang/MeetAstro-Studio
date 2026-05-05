"""
Request/Response Pydantic schemas cho meetings API.

Tách biệt với src/schema.py để tránh ô nhiễm domain models.
"""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class MeetingCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    # NOTE: DB (migration 0003) stores user_id as UUID. If omitted, backend will use a zero UUID.
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

    model_config = {"from_attributes": True}


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

    model_config = {"from_attributes": True}


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

    model_config = {"from_attributes": True}


class AudioUploadResponse(BaseModel):
    meeting_id: UUID
    job_id: str
    audio_storage_path: Optional[str] = None
    audio_duration_seconds: Optional[float] = None
    status: str = "queued"
    message: str = "Pipeline đã được queue. Dùng /jobs/{job_id} để theo dõi tiến trình."
