"""Shorten long URLs and resolve short codes."""

from collections.abc import Callable
from datetime import datetime

from sqlalchemy import ScalarSelect, Select, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from shorten_me.aliases import validate_alias
from shorten_me.codec import InvalidShortCode, decode, encode
from shorten_me.models import Alias, Link
from shorten_me.urls import validate_long_url


class LinkNotFound(LookupError):
    """Raised when a short code doesn't belong to any link."""


class AliasTaken(ValueError):
    """Raised when a custom alias already belongs to a different link."""


class LinkService:
    """Link operations, each committed as one unit of work on the given session."""

    def __init__(self, session: Session, clock: Callable[[], datetime]) -> None:
        self._session = session
        self._clock = clock

    def shorten(self, long_url: str, alias: str | None = None) -> str:
        """Return the short code for a URL, creating its link on first use.

        With an alias, the alias is attached to the link and returned as its code.
        """
        validate_long_url(long_url)
        if alias is not None:
            validate_alias(alias)
        link = self._find(long_url)
        if link is None:
            link = self._create(long_url)
        code = encode(link.id) if alias is None else self._claim(alias, link)
        self._session.commit()
        return code

    def find(self, code: str) -> Link:
        """Return the link for a short code without counting a hit."""
        link = self._session.scalar(select(Link).where(Link.id == _link_id(code)))
        if link is None:
            raise LinkNotFound(code)
        return link

    def resolve(self, code: str) -> str:
        """Count a hit on a short code and return its long URL."""
        count_hit = update(Link).where(Link.id == _link_id(code)).values(hits=Link.hits + 1)
        long_url = self._session.scalar(count_hit.returning(Link.long_url))
        if long_url is None:
            raise LinkNotFound(code)
        self._session.commit()
        return long_url

    def _find(self, long_url: str) -> Link | None:
        return self._session.scalar(_by_url(long_url))

    def _create(self, long_url: str) -> Link:
        link = Link(long_url=long_url, created_at=self._clock())
        try:
            with self._session.begin_nested():
                self._session.add(link)
        except IntegrityError:
            # Another request inserted the same URL between our lookup and insert.
            return self._session.scalars(_by_url(long_url)).one()
        return link

    def _claim(self, alias: str, link: Link) -> str:
        try:
            with self._session.begin_nested():
                self._session.add(Alias(name=alias, link_id=link.id))
        except IntegrityError:
            # The alias exists, possibly inserted by a concurrent request for the same URL.
            if self._session.get_one(Alias, alias).link_id != link.id:
                raise AliasTaken(alias) from None
        return alias


def _link_id(code: str) -> int | ScalarSelect[int]:
    try:
        return decode(code)
    except InvalidShortCode:
        # Aliases never decode, so a code that doesn't is looked up as one.
        return select(Alias.link_id).where(Alias.name == code).scalar_subquery()


def _by_url(long_url: str) -> Select[tuple[Link]]:
    return select(Link).where(Link.long_url == long_url)
