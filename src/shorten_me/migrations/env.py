"""Alembic environment: migrate the database passed by `schema` or named in the settings."""

from alembic import context
from sqlalchemy import create_engine, pool

from shorten_me.models import Base
from shorten_me.settings import Settings

if context.is_offline_mode():
    raise NotImplementedError("offline (--sql) migrations are not supported")

url = context.config.attributes.get("database_url") or Settings().database_url
# Not `create_db_engine`: with foreign keys enforced, SQLite can't rebuild a referenced table.
engine = create_engine(url, poolclass=pool.NullPool)
with engine.connect() as connection:
    # SQLite can't ALTER most things in place; batch mode rebuilds the table instead.
    context.configure(connection=connection, target_metadata=Base.metadata, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()
