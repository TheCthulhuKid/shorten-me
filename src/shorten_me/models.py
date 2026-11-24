"""Database tables."""

from datetime import UTC, datetime

from sqlalchemy import (
    DateTime,
    Dialect,
    ForeignKey,
    Index,
    MetaData,
    String,
    TypeDecorator,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from shorten_me.aliases import MAX_ALIAS_LENGTH
from shorten_me.urls import MAX_URL_LENGTH


class Base(DeclarativeBase):
    """Declarative base for all tables."""

    # Named constraints let SQLite batch migrations find them again.
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(table_name)s_%(column_0_name)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


class UtcDateTime(TypeDecorator[datetime]):
    """An aware datetime, stored in UTC and loaded as UTC.

    SQLite drops the offset, so without this it would return naive datetimes and compare
    datetimes from different timezones as text.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError(f"datetime must include a timezone, got {value!r}")
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class Link(Base):
    """A long URL and how often its short code has been followed.

    A URL has at most one permanent link, and any number of links that expire.
    """

    __tablename__ = "links"
    __table_args__ = (
        Index(
            "uq_links_permanent_long_url",
            "long_url",
            unique=True,
            sqlite_where=text("expires_at IS NULL"),
            postgresql_where=text("expires_at IS NULL"),
        ),
        {"sqlite_autoincrement": True},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    long_url: Mapped[str] = mapped_column(String(MAX_URL_LENGTH))
    hits: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime)
    expires_at: Mapped[datetime | None] = mapped_column(UtcDateTime)


class Alias(Base):
    """A custom short code chosen by a client for a link."""

    __tablename__ = "aliases"

    name: Mapped[str] = mapped_column(String(MAX_ALIAS_LENGTH), primary_key=True)
    link_id: Mapped[int] = mapped_column(ForeignKey(Link.id, ondelete="CASCADE"), index=True)
