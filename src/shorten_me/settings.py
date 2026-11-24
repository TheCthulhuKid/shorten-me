"""Service settings, read from `SHORTEN_ME_*` environment variables."""

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Where the service listens and is reached, its proxies, database and rate limit."""

    model_config = SettingsConfigDict(env_prefix="SHORTEN_ME_")

    database_url: str = "sqlite:///shorten_me.db"
    host: str = "127.0.0.1"
    port: int = 8000
    public_url: HttpUrl | None = None
    rate_limit: int = Field(default=10, ge=0)
    proxy_headers: bool = True
    forwarded_allow_ips: str = "127.0.0.1,::1"
