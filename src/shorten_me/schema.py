"""Connect to a database and bring it up to the latest schema."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, Engine, create_engine, event, make_url
from sqlalchemy.engine.interfaces import DBAPIConnection
from sqlalchemy.pool import ConnectionPoolEntry


class DatabaseNotFound(FileNotFoundError):
    """Raised when a SQLite database file doesn't exist and connecting would create it."""


def create_db_engine(database_url: str) -> Engine:
    """Return an engine on which SQLite enforces foreign keys and rolls back savepoints.

    SQLite does neither unless asked; other databases do both.
    """
    engine = create_engine(database_url)
    if engine.dialect.name == "sqlite":
        event.listen(engine, "connect", _configure_sqlite)
        event.listen(engine, "begin", _begin_immediate)
    return engine


def _configure_sqlite(connection: DBAPIConnection, _record: ConnectionPoolEntry) -> None:
    # sqlite3 opens no transaction before a SAVEPOINT, so releasing one would commit it.
    # Turning its own BEGIN off lets `_begin_immediate` open every transaction instead.
    connection.isolation_level = None
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.close()


def _begin_immediate(connection: Connection) -> None:
    # IMMEDIATE takes the write lock up front. A transaction that reads first and then
    # writes would otherwise fail with "database is locked" when another one is writing.
    connection.exec_driver_sql("BEGIN IMMEDIATE")


def alembic_config(database_url: str) -> Config:
    """Return an Alembic config for the bundled migrations and the given database."""
    config = Config()
    config.set_main_option("script_location", "shorten_me:migrations")
    config.attributes["database_url"] = database_url
    return config


def require_database(database_url: str) -> None:
    """Raise `DatabaseNotFound` if the URL names a SQLite file that doesn't exist."""
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite" or url.database in (None, "", ":memory:"):
        return
    path = Path(url.database).resolve()
    if not path.exists():
        raise DatabaseNotFound(f"no database at {path}; check SHORTEN_ME_DATABASE_URL")


def upgrade_to_head(database_url: str) -> None:
    """Apply every migration the database hasn't had yet."""
    command.upgrade(alembic_config(database_url), "head")
