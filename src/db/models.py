"""
SQLAlchemy ORM models for AI Meeting Assistant (PostgreSQL).

Tables:
- meetings: Meeting records (pipeline entry point)
- transcripts: Transcript data (supports vector search)
- analysis_results: GPT-4o analysis results
- review_items: Human-in-the-loop review items
- provider_configs: Provider credentials (encrypted)
- user_plans: User subscription plans (for quota management)
- usage_records: Token/API usage tracking
- quota_limits: Plan-based limits configuration

UUID primary keys, TIMESTAMPTZ timestamps.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base


def _now() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc)


class Meeting(Base):
    """Meeting record - entry point of the processing pipeline."""

    __tablename__ = "meetings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    audio_path: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    user_id: Mapped[str] = mapped_column(Text, nullable=False, default="default_user")
    celery_task_id: Mapped[Optional[str]] = mapped_column(Text)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )

    transcript: Mapped[Optional["Transcript"]] = relationship(
        back_populates="meeting", uselist=False, cascade="all, delete-orphan"
    )
    analysis: Mapped[Optional["AnalysisResult"]] = relationship(
        back_populates="meeting", uselist=False, cascade="all, delete-orphan"
    )
    review_items: Mapped[list["ReviewItem"]] = relationship(
        back_populates="meeting", cascade="all, delete-orphan"
    )


class Transcript(Base):
    """Transcript stored separately - supports vector search and Q&A bot."""

    __tablename__ = "transcripts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    diarized_text: Mapped[Optional[str]] = mapped_column(Text)
    language: Mapped[str] = mapped_column(Text, default="en")
    char_count: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )

    meeting: Mapped["Meeting"] = relationship(back_populates="transcript")


class AnalysisResult(Base):
    """GPT-4o analysis result - JSON blob + metadata."""

    __tablename__ = "analysis_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    analysis_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text)
    overall_confidence: Mapped[Optional[float]] = mapped_column(Float)
    validation_metrics: Mapped[Optional[dict]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )

    meeting: Mapped["Meeting"] = relationship(back_populates="analysis")


class ReviewItem(Base):
    """Single item awaiting human review - flattened from Epic/Task/Subtask."""

    __tablename__ = "review_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    item_type: Mapped[str] = mapped_column(Text, nullable=False)
    item_index: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    assignee: Mapped[Optional[str]] = mapped_column(Text)
    deadline: Mapped[Optional[str]] = mapped_column(Text)
    priority: Mapped[Optional[str]] = mapped_column(Text)
    context: Mapped[Optional[str]] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    is_flagged: Mapped[bool] = mapped_column(Boolean, default=False)
    review_status: Mapped[str] = mapped_column(Text, default="draft")
    edited_summary: Mapped[Optional[str]] = mapped_column(Text)
    edited_assignee: Mapped[Optional[str]] = mapped_column(Text)
    edited_deadline: Mapped[Optional[str]] = mapped_column(Text)
    edited_priority: Mapped[Optional[str]] = mapped_column(Text)
    validation_notes: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )

    meeting: Mapped["Meeting"] = relationship(back_populates="review_items")


class ProviderConfig(Base):
    """Provider credentials - Fernet-encrypted JSON."""

    __tablename__ = "provider_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[str] = mapped_column(Text, nullable=False, default="default_user")
    provider_name: Mapped[str] = mapped_column(Text, nullable=False)
    config_json: Mapped[str] = mapped_column(Text, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )

    __table_args__ = (UniqueConstraint("user_id", "provider_name", name="uq_user_provider"),)


class UserPlan(Base):
    """
    User subscription plan for quota management.

    Plan types: free, basic, pro, enterprise
    Each plan has different quota limits defined in QuotaLimit table.
    """

    __tablename__ = "user_plans"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    plan_type: Mapped[str] = mapped_column(Text, nullable=False, default="free")
    plan_started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
    plan_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    extra_data: Mapped[Optional[dict]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )

    usage_records: Mapped[list["UsageRecord"]] = relationship(
        back_populates="user_plan", cascade="all, delete-orphan"
    )


class UsageRecord(Base):
    """
    Token and API usage tracking per user.

    Tracks daily/monthly usage for quota enforcement.
    Usage types: transcription_tokens, analysis_tokens, jira_pushes, meetings
    """

    __tablename__ = "usage_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_plans.id", ondelete="CASCADE"), nullable=False
    )
    usage_type: Mapped[str] = mapped_column(Text, nullable=False)
    usage_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    extra_data: Mapped[Optional[dict]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )

    user_plan: Mapped["UserPlan"] = relationship(back_populates="usage_records")

    __table_args__ = (
        Index("ix_usage_user_type_period", "user_plan_id", "usage_type", "period_start"),
        UniqueConstraint(
            "user_plan_id", "usage_type", "period_start",
            name="uq_usage_user_type_period"
        ),
    )


class QuotaLimit(Base):
    """
    Quota limits configuration per plan type.

    Defines maximum allowed usage for each plan.
    Limit types match usage_type in UsageRecord.
    """

    __tablename__ = "quota_limits"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    plan_type: Mapped[str] = mapped_column(Text, nullable=False)
    limit_type: Mapped[str] = mapped_column(Text, nullable=False)
    limit_value: Mapped[int] = mapped_column(BigInteger, nullable=False)
    period_type: Mapped[str] = mapped_column(Text, nullable=False, default="monthly")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )

    __table_args__ = (
        UniqueConstraint(
            "plan_type", "limit_type", "period_type",
            name="uq_plan_limit_period"
        ),
    )
