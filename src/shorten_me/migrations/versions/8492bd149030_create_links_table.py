"""create links table

Revision ID: 8492bd149030
Revises:
Create Date: 2026-11-23 17:22:21.792611
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "8492bd149030"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("long_url", sa.String(length=2048), nullable=False),
        sa.Column("hits", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_links")),
        sa.UniqueConstraint("long_url", name=op.f("uq_links_long_url")),
    )


def downgrade() -> None:
    op.drop_table("links")
