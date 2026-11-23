"""Bring a database up to the latest schema."""

from alembic import command
from alembic.config import Config


def alembic_config(database_url: str) -> Config:
    """Return an Alembic config for the bundled migrations and the given database."""
    config = Config()
    config.set_main_option("script_location", "shorten_me:migrations")
    config.attributes["database_url"] = database_url
    return config


def upgrade_to_head(database_url: str) -> None:
    """Apply every migration the database hasn't had yet."""
    command.upgrade(alembic_config(database_url), "head")
