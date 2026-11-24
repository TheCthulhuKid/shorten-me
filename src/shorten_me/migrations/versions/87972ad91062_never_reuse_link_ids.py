"""never reuse link ids

Revision ID: 87972ad91062
Revises: caef61b9fa3b
Create Date: 2026-11-24 10:13:47.635127
"""

from collections.abc import Sequence

from alembic import op

revision: str = "87972ad91062"
down_revision: str | Sequence[str] | None = "caef61b9fa3b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    _rebuild_links(autoincrement=True)


def downgrade() -> None:
    _rebuild_links(autoincrement=False)


def _rebuild_links(autoincrement: bool) -> None:
    # Other databases never reuse sequence values; SQLite does unless the table says AUTOINCREMENT.
    if op.get_bind().dialect.name != "sqlite":
        return
    with op.batch_alter_table(
        "links", recreate="always", table_kwargs={"sqlite_autoincrement": autoincrement}
    ):
        pass
