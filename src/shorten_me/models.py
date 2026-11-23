"""Database tables."""

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from shorten_me.urls import MAX_URL_LENGTH


class Base(DeclarativeBase):
    """Declarative base for all tables."""


class Link(Base):
    """A long URL and how often its short code has been followed."""

    __tablename__ = "links"

    id: Mapped[int] = mapped_column(primary_key=True)
    long_url: Mapped[str] = mapped_column(String(MAX_URL_LENGTH), unique=True)
    hits: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
