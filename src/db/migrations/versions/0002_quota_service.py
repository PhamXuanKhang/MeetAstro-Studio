"""Add quota service tables: user_plans, usage_records, quota_limits

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-24
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_plans",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", sa.Text(), nullable=False, unique=True),
        sa.Column("plan_type", sa.Text(), nullable=False, server_default="free"),
        sa.Column(
            "plan_started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("plan_expires_at", sa.DateTime(timezone=True)),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("extra_data", postgresql.JSONB()),
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
    op.create_index("ix_user_plans_user_id", "user_plans", ["user_id"])

    op.create_table(
        "usage_records",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_plan_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user_plans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("usage_type", sa.Text(), nullable=False),
        sa.Column("usage_count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("extra_data", postgresql.JSONB()),
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
        sa.UniqueConstraint(
            "user_plan_id", "usage_type", "period_start",
            name="uq_usage_user_type_period",
        ),
    )
    op.create_index(
        "ix_usage_user_type_period",
        "usage_records",
        ["user_plan_id", "usage_type", "period_start"],
    )

    op.create_table(
        "quota_limits",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("plan_type", sa.Text(), nullable=False),
        sa.Column("limit_type", sa.Text(), nullable=False),
        sa.Column("limit_value", sa.BigInteger(), nullable=False),
        sa.Column("period_type", sa.Text(), nullable=False, server_default="monthly"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("description", sa.Text()),
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
        sa.UniqueConstraint(
            "plan_type", "limit_type", "period_type",
            name="uq_plan_limit_period",
        ),
    )
    op.create_index("ix_quota_limits_plan_type", "quota_limits", ["plan_type"])


def downgrade() -> None:
    op.drop_index("ix_quota_limits_plan_type", "quota_limits")
    op.drop_table("quota_limits")
    op.drop_index("ix_usage_user_type_period", "usage_records")
    op.drop_table("usage_records")
    op.drop_index("ix_user_plans_user_id", "user_plans")
    op.drop_table("user_plans")
