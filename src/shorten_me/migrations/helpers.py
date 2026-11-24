"""Helpers shared by the migration scripts."""

from collections.abc import Iterator
from contextlib import contextmanager

import sqlalchemy as sa
from alembic import op
from alembic.operations import BatchOperations


@contextmanager
def alter_links() -> Iterator[BatchOperations]:
    """Batch-alter `links` without letting SQLite hand out a deleted link's id again.

    Rebuilding the table drops AUTOINCREMENT unless it is asked for again, and resets the
    counter of the highest id ever used to the highest id still in the table.
    """
    bind = op.get_bind()
    counter = None
    if bind.dialect.name == "sqlite":
        counter = bind.scalar(sa.text("SELECT seq FROM sqlite_sequence WHERE name = 'links'"))
    with op.batch_alter_table("links", table_kwargs={"sqlite_autoincrement": True}) as batch_op:
        yield batch_op
    if counter is not None:
        op.execute("DELETE FROM sqlite_sequence WHERE name = 'links'")
        op.execute(
            sa.text("INSERT INTO sqlite_sequence VALUES ('links', :seq)").bindparams(seq=counter)
        )
