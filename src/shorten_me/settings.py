"""Service settings, read from `SHORTEN_ME_*` environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Where the service listens and which database it uses."""

    model_config = SettingsConfigDict(env_prefix="SHORTEN_ME_")

    database_url: str = "sqlite:///shorten_me.db"
    host: str = "127.0.0.1"
    port: int = 8000
    debug: bool = False
