from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import NullPool, create_engine, text

from shorten_me.models import Base
from shorten_me.schema import alembic_config, create_db_engine, upgrade_to_head


def test_migrations_match_the_models(database_url):
    upgrade_to_head(database_url)
    with create_engine(database_url, poolclass=NullPool).connect() as connection:
        assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []


def test_migrations_downgrade_and_upgrade_cleanly(database_url):
    config = alembic_config(database_url)
    command.upgrade(config, "head")
    command.downgrade(config, "base")
    command.upgrade(config, "head")


def test_migrated_links_table_never_reuses_ids(database_url):
    upgrade_to_head(database_url)
    with create_engine(database_url, poolclass=NullPool).connect() as connection:
        ddl = connection.scalar(text("SELECT sql FROM sqlite_master WHERE name = 'links'"))
    assert "AUTOINCREMENT" in ddl


def test_migrated_database_deletes_aliases_with_their_link(database_url):
    upgrade_to_head(database_url)
    engine = create_db_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO links VALUES (1, 'https://example.com/a', 0, :now, NULL)"),
            {"now": "2026-01-01"},
        )
        connection.execute(text("INSERT INTO aliases VALUES ('my-link', 1)"))
        connection.execute(text("DELETE FROM links"))
        assert connection.scalar(text("SELECT count(*) FROM aliases")) == 0
    engine.dispose()
