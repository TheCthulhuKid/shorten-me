from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine

from shorten_me.models import Base
from shorten_me.schema import alembic_config, upgrade_to_head


def test_migrations_match_the_models(tmp_path):
    url = f"sqlite:///{tmp_path / 'test.db'}"
    upgrade_to_head(url)
    with create_engine(url).connect() as connection:
        assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []


def test_migrations_downgrade_and_upgrade_cleanly(tmp_path):
    config = alembic_config(f"sqlite:///{tmp_path / 'test.db'}")
    command.upgrade(config, "head")
    command.downgrade(config, "base")
    command.upgrade(config, "head")
