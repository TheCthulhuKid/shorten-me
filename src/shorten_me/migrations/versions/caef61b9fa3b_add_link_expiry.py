"""add link expiry

Revision ID: caef61b9fa3b
Revises: dda13c8dd9ee
Create Date: 2026-11-23 17:52:00.147339
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "caef61b9fa3b"
down_revision: str | Sequence[str] | None = "dda13c8dd9ee"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("links", schema=None) as batch_op:
        batch_op.add_column(sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("links", schema=None) as batch_op:
        batch_op.drop_column("expires_at")
