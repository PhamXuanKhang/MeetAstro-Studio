"""Add meeting audio ingestion fields.

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-05
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("meetings", sa.Column("audio_storage_path", sa.Text(), nullable=True))
    op.add_column("meetings", sa.Column("audio_duration_seconds", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("meetings", "audio_duration_seconds")
    op.drop_column("meetings", "audio_storage_path")

