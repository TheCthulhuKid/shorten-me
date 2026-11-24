"""Shorten long URLs and resolve short codes."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import (
    ColumnElement,
    Engine,
    ScalarSelect,
    Select,
    and_,
    delete,
    or_,
    select,
    update,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from shorten_me.aliases import validate_alias
from shorten_me.codec import InvalidShortCode, decode, encode
from shorten_me.expiry import expiry_in_utc
from shorten_me.models import Alias, Link
from shorten_me.urls import validate_long_url


class LinkNotFound(LookupError):
    """Raised when a short code doesn't belong to any link."""


class LinkExpired(LookupError):
    """Raised when a short code belongs to a link whose expiry has passed."""


class AliasTaken(Exception):
    """Raised when a custom alias already belongs to a different link."""


class InvalidGracePeriod(ValueError):
    """Raised when a cleanup grace period is negative or too long to subtract from now."""


@dataclass(frozen=True)
class ShortLink:
    """The code handed out for a long URL, and when its link expires."""

    code: str
    expires_at: datetime | None


class LinkService:
    """Link operations, each committed as one unit of work on the given session.

    The clock must return timezone-aware datetimes. With `public_url`, the address clients
    reach this service at, links that point back at the service are refused.
    """

    def __init__(
        self, session: Session, clock: Callable[[], datetime], public_url: str | None = None
    ) -> None:
        self._session = session
        self._clock = clock
        self._public_url = public_url

    def shorten(
        self, long_url: str, alias: str | None = None, expires_at: datetime | None = None
    ) -> ShortLink:
        """Return the short code for a URL and its expiry, creating its link on first use.

        With an alias, the alias is attached to the link and returned as its code. An existing
        link's expiry is only ever pushed later, and no expiry means the link never expires.
        """
        validate_long_url(long_url, own_url=self._public_url)
        if alias is not None:
            validate_alias(alias)
        if expires_at is not None:
            expires_at = expiry_in_utc(expires_at, self._clock())
        link = self._find_by_url(long_url)
        if link is None:
            link = self._create(long_url, expires_at)
        self._extend(link, expires_at)
        code = encode(link.id) if alias is None else self._claim(alias, link)
        short_link = ShortLink(code, link.expires_at)
        self._session.commit()
        return short_link

    def find(self, code: str) -> Link:
        """Return the link for a short code without counting a hit."""
        link = self._session.scalar(select(Link).where(Link.id == _link_id(code)))
        if link is None:
            raise LinkNotFound(code)
        return link

    def resolve(self, code: str) -> str:
        """Count a hit on a short code and return its long URL, if the link hasn't expired."""
        count_hit = update(Link).where(self._is_live(code)).values(hits=Link.hits + 1)
        long_url = self._session.scalar(count_hit.returning(Link.long_url))
        if long_url is None:
            raise self._why_not_live(code)
        self._session.commit()
        return long_url

    def preview(self, code: str) -> str:
        """Return a short code's long URL without counting a hit, if the link hasn't expired."""
        long_url = self._session.scalar(select(Link.long_url).where(self._is_live(code)))
        if long_url is None:
            raise self._why_not_live(code)
        return long_url

    def delete_expired(self, grace: timedelta) -> int:
        """Delete links that expired more than `grace` ago and return the count.

        The database deletes their aliases with them.
        """
        if grace < timedelta(0):
            raise InvalidGracePeriod(f"grace period must not be negative, got {grace}")
        try:
            cutoff = self._clock() - grace
        except OverflowError as error:
            raise InvalidGracePeriod(f"grace period is too long, got {grace}") from error
        deleted = self._session.execute(delete(Link).where(Link.expires_at < cutoff)).rowcount
        self._session.commit()
        return deleted

    def _is_live(self, code: str) -> ColumnElement[bool]:
        not_expired = or_(Link.expires_at.is_(None), Link.expires_at > self._clock())
        return and_(Link.id == _link_id(code), not_expired)

    def _why_not_live(self, code: str) -> LookupError:
        exists = self._session.scalar(select(Link.id).where(Link.id == _link_id(code)))
        return LinkNotFound(code) if exists is None else LinkExpired(code)

    def _find_by_url(self, long_url: str) -> Link | None:
        return self._session.scalar(_by_url(long_url))

    def _create(self, long_url: str, expires_at: datetime | None) -> Link:
        link = Link(long_url=long_url, created_at=self._clock(), expires_at=expires_at)
        try:
            with self._session.begin_nested():
                self._session.add(link)
        except IntegrityError:
            # Another request inserted the same URL between our lookup and insert.
            existing = self._find_by_url(long_url)
            if existing is None:
                raise
            return existing
        return link

    def _extend(self, link: Link, expires_at: datetime | None) -> None:
        # A single conditional UPDATE, so concurrent requests can't move the expiry earlier.
        extend = update(Link).where(Link.id == link.id, Link.expires_at.is_not(None))
        if expires_at is not None:
            extend = extend.where(Link.expires_at < expires_at)
        self._session.execute(extend.values(expires_at=expires_at))

    def _claim(self, alias: str, link: Link) -> str:
        try:
            with self._session.begin_nested():
                self._session.add(Alias(name=alias, link_id=link.id))
        except IntegrityError:
            # The alias exists, possibly inserted by a concurrent request for the same URL.
            existing = self._session.get(Alias, alias)
            if existing is None:
                raise
            if existing.link_id != link.id:
                raise AliasTaken(alias) from None
        return alias


@contextmanager
def open_service(
    engine: Engine, clock: Callable[[], datetime], public_url: str | None = None
) -> Iterator[LinkService]:
    """Yield a `LinkService` on a session of its own, closed afterwards."""
    with Session(engine) as session:
        yield LinkService(session, clock, public_url)


def _link_id(code: str) -> int | ScalarSelect[int]:
    try:
        return decode(code)
    except InvalidShortCode:
        # Aliases never decode, so a code that doesn't is looked up as one.
        return select(Alias.link_id).where(Alias.name == code).scalar_subquery()


def _by_url(long_url: str) -> Select[tuple[Link]]:
    return select(Link).where(Link.long_url == long_url)
