"""create aliases table

Revision ID: dda13c8dd9ee
Revises: 8492bd149030
Create Date: 2026-11-23 17:37:33.291304
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "dda13c8dd9ee"
down_revision: str | Sequence[str] | None = "8492bd149030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "aliases",
        sa.Column("name", sa.String(length=32), nullable=False),
        sa.Column("link_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["link_id"], ["links.id"], name=op.f("fk_aliases_link_id_links")),
        sa.PrimaryKeyConstraint("name", name=op.f("pk_aliases")),
    )


def downgrade() -> None:
    op.drop_table("aliases")
