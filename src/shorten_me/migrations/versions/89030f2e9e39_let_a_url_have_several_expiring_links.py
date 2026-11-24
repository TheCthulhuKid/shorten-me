"""let a url have several expiring links

Revision ID: 89030f2e9e39
Revises: 096e31de8f7a
Create Date: 2026-11-24 14:07:34.852095
"""

from collections.abc import Sequence

import sqlalchemy as sa

from shorten_me.migrations.helpers import alter_links

revision: str = "89030f2e9e39"
down_revision: str | Sequence[str] | None = "096e31de8f7a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with alter_links() as batch_op:
        batch_op.drop_constraint(batch_op.f("uq_links_long_url"), type_="unique")
        batch_op.create_index(
            "uq_links_permanent_long_url",
            ["long_url"],
            unique=True,
            sqlite_where=sa.text("expires_at IS NULL"),
            postgresql_where=sa.text("expires_at IS NULL"),
        )


def downgrade() -> None:
    # Fails if a URL has several links by now; delete the extra ones first.
    with alter_links() as batch_op:
        batch_op.drop_index(
            "uq_links_permanent_long_url",
            sqlite_where=sa.text("expires_at IS NULL"),
            postgresql_where=sa.text("expires_at IS NULL"),
        )
        batch_op.create_unique_constraint(batch_op.f("uq_links_long_url"), ["long_url"])
