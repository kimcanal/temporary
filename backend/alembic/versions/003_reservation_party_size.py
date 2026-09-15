"""add reservations.party_size

Revision ID: 003
Revises: 002
Create Date: 2026-09-15
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "reservations",
        sa.Column("party_size", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_check_constraint(
        "ck_reservation_positive_party_size", "reservations", "party_size > 0"
    )


def downgrade() -> None:
    op.drop_constraint("ck_reservation_positive_party_size", "reservations", type_="check")
    op.drop_column("reservations", "party_size")
