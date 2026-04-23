"""Initial schema: meetings, transcripts, analysis_results, review_items, provider_configs

Revision ID: 0001
Revises:
Create Date: 2026-04-22
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    op.create_table(
        "meetings",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("audio_path", sa.Text()),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("user_id", sa.Text(), nullable=False, server_default="default_user"),
        sa.Column("celery_task_id", sa.Text()),
        sa.Column("error_message", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "transcripts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "meeting_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("meetings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("diarized_text", sa.Text()),
        sa.Column("language", sa.Text(), server_default="en"),
        sa.Column("char_count", sa.Integer()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "analysis_results",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "meeting_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("meetings.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("analysis_json", postgresql.JSONB(), nullable=False),
        sa.Column("summary", sa.Text()),
        sa.Column("overall_confidence", sa.Float()),
        sa.Column("validation_metrics", postgresql.JSONB()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "review_items",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "meeting_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("meetings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("item_type", sa.Text(), nullable=False),
        sa.Column("item_index", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("assignee", sa.Text()),
        sa.Column("deadline", sa.Text()),
        sa.Column("priority", sa.Text()),
        sa.Column("context", sa.Text()),
        sa.Column("confidence", sa.Float(), server_default="0.0"),
        sa.Column("is_flagged", sa.Boolean(), server_default="false"),
        sa.Column("review_status", sa.Text(), server_default="draft"),
        sa.Column("edited_summary", sa.Text()),
        sa.Column("edited_assignee", sa.Text()),
        sa.Column("edited_deadline", sa.Text()),
        sa.Column("edited_priority", sa.Text()),
        sa.Column("validation_notes", postgresql.JSONB(), server_default=sa.text("'[]'")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_review_items_meeting_id", "review_items", ["meeting_id"])
    op.create_index("ix_review_items_is_flagged", "review_items", ["is_flagged"])

    op.create_table(
        "provider_configs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", sa.Text(), nullable=False, server_default="default_user"),
        sa.Column("provider_name", sa.Text(), nullable=False),
        sa.Column("config_json", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("user_id", "provider_name", name="uq_user_provider"),
    )


def downgrade() -> None:
    op.drop_table("provider_configs")
    op.drop_index("ix_review_items_is_flagged", "review_items")
    op.drop_index("ix_review_items_meeting_id", "review_items")
    op.drop_table("review_items")
    op.drop_table("analysis_results")
    op.drop_table("transcripts")
    op.drop_table("meetings")
