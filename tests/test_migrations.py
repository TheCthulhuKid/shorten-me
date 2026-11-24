from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import NullPool, create_engine, text

from shorten_me.models import Base
from shorten_me.schema import alembic_config, create_db_engine, upgrade_to_head


def test_migrations_match_the_models(tmp_path):
    url = f"sqlite:///{tmp_path / 'test.db'}"
    upgrade_to_head(url)
    with create_engine(url, poolclass=NullPool).connect() as connection:
        assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []


def test_migrations_downgrade_and_upgrade_cleanly(tmp_path):
    config = alembic_config(f"sqlite:///{tmp_path / 'test.db'}")
    command.upgrade(config, "head")
    command.downgrade(config, "base")
    command.upgrade(config, "head")


def test_migrated_links_table_never_reuses_ids(tmp_path):
    url = f"sqlite:///{tmp_path / 'test.db'}"
    upgrade_to_head(url)
    with create_engine(url, poolclass=NullPool).connect() as connection:
        ddl = connection.scalar(text("SELECT sql FROM sqlite_master WHERE name = 'links'"))
    assert "AUTOINCREMENT" in ddl


def test_migrated_database_deletes_aliases_with_their_link(tmp_path):
    url = f"sqlite:///{tmp_path / 'test.db'}"
    upgrade_to_head(url)
    engine = create_db_engine(url)
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO links VALUES (1, 'https://example.com/a', 0, :now, NULL)"),
            {"now": "2026-01-01"},
        )
        connection.execute(text("INSERT INTO aliases VALUES ('my-link', 1)"))
        connection.execute(text("DELETE FROM links"))
        assert connection.scalar(text("SELECT count(*) FROM aliases")) == 0
    engine.dispose()
