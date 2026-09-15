"""app_settings table for admin-tunable business rules

Revision ID: 002
Revises: 001
Create Date: 2026-09-15
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "app_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("daily_limit_hours", sa.Float(), nullable=False),
        sa.Column("slot_minutes", sa.Integer(), nullable=False),
        sa.Column("checkin_grace_minutes", sa.Integer(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("app_settings")
