"""Database tables."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, MetaData, String
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


class Link(Base):
    """A long URL and how often its short code has been followed."""

    __tablename__ = "links"

    id: Mapped[int] = mapped_column(primary_key=True)
    long_url: Mapped[str] = mapped_column(String(MAX_URL_LENGTH), unique=True)
    hits: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Alias(Base):
    """A custom short code chosen by a client for a link."""

    __tablename__ = "aliases"

    name: Mapped[str] = mapped_column(String(MAX_ALIAS_LENGTH), primary_key=True)
    link_id: Mapped[int] = mapped_column(ForeignKey(Link.id))
