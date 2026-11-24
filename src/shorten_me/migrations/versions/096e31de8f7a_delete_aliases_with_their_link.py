"""delete aliases with their link

Revision ID: 096e31de8f7a
Revises: 87972ad91062
Create Date: 2026-11-24 12:00:22.195154
"""

from collections.abc import Sequence

from alembic import op

revision: str = "096e31de8f7a"
down_revision: str | Sequence[str] | None = "87972ad91062"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DELETE FROM aliases WHERE link_id NOT IN (SELECT id FROM links)")
    with op.batch_alter_table("aliases", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_aliases_link_id"), ["link_id"], unique=False)
        batch_op.drop_constraint(batch_op.f("fk_aliases_link_id_links"), type_="foreignkey")
        batch_op.create_foreign_key(
            batch_op.f("fk_aliases_link_id_links"), "links", ["link_id"], ["id"], ondelete="CASCADE"
        )


def downgrade() -> None:
    with op.batch_alter_table("aliases", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("fk_aliases_link_id_links"), type_="foreignkey")
        batch_op.create_foreign_key(
            batch_op.f("fk_aliases_link_id_links"), "links", ["link_id"], ["id"]
        )
        batch_op.drop_index(batch_op.f("ix_aliases_link_id"))
