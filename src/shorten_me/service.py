"""Shorten long URLs and resolve short codes."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy import ScalarSelect, Select, delete, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from shorten_me.aliases import validate_alias
from shorten_me.codec import InvalidShortCode, decode, encode
from shorten_me.models import Alias, Link
from shorten_me.urls import validate_long_url


class LinkNotFound(LookupError):
    """Raised when a short code doesn't belong to any link."""


class LinkExpired(LookupError):
    """Raised when a short code belongs to a link whose expiry has passed."""


class InvalidExpiry(ValueError):
    """Raised when a requested expiry has no timezone or isn't in the future."""


class AliasTaken(ValueError):
    """Raised when a custom alias already belongs to a different link."""


class LinkService:
    """Link operations, each committed as one unit of work on the given session."""

    def __init__(self, session: Session, clock: Callable[[], datetime]) -> None:
        self._session = session
        self._clock = clock

    def shorten(
        self, long_url: str, alias: str | None = None, expires_at: datetime | None = None
    ) -> str:
        """Return the short code for a URL, creating its link on first use.

        With an alias, the alias is attached to the link and returned as its code. An existing
        link's expiry is only ever pushed later, and no expiry means the link never expires.
        """
        validate_long_url(long_url)
        if alias is not None:
            validate_alias(alias)
        if expires_at is not None:
            expires_at = self._future_utc(expires_at)
        link = self._find(long_url)
        if link is None:
            link = self._create(long_url, expires_at)
        self._extend(link, expires_at)
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
        """Count a hit on a short code and return its long URL, if the link hasn't expired."""
        live = or_(Link.expires_at.is_(None), Link.expires_at > self._clock())
        count_hit = update(Link).where(Link.id == _link_id(code), live).values(hits=Link.hits + 1)
        long_url = self._session.scalar(count_hit.returning(Link.long_url))
        if long_url is None:
            self.find(code)
            raise LinkExpired(code)
        self._session.commit()
        return long_url

    def delete_expired(self, grace: timedelta) -> int:
        """Delete links that expired more than `grace` ago, with their aliases; return the count."""
        if grace < timedelta(0):
            raise ValueError(f"grace period must not be negative, got {grace}")
        expired = select(Link.id).where(Link.expires_at < self._clock() - grace)
        self._session.execute(delete(Alias).where(Alias.link_id.in_(expired)))
        deleted = self._session.execute(delete(Link).where(Link.id.in_(expired))).rowcount
        self._session.commit()
        return deleted

    def _find(self, long_url: str) -> Link | None:
        return self._session.scalar(_by_url(long_url))

    def _future_utc(self, expires_at: datetime) -> datetime:
        if expires_at.tzinfo is None:
            raise InvalidExpiry("expiry must include a timezone")
        try:
            # SQLite stores datetimes without their offset, so all of them must be in UTC.
            expires_at = expires_at.astimezone(UTC)
        except OverflowError as error:
            raise InvalidExpiry("expiry is out of range") from error
        if expires_at <= self._clock():
            raise InvalidExpiry("expiry must be in the future")
        return expires_at

    def _create(self, long_url: str, expires_at: datetime | None) -> Link:
        link = Link(long_url=long_url, created_at=self._clock(), expires_at=expires_at)
        try:
            with self._session.begin_nested():
                self._session.add(link)
        except IntegrityError:
            # Another request inserted the same URL between our lookup and insert.
            return self._session.scalars(_by_url(long_url)).one()
        return link

    def _extend(self, link: Link, expires_at: datetime | None) -> None:
        # A single conditional UPDATE, so concurrent requests can't move the expiry earlier.
        extend = update(Link).where(Link.id == link.id, Link.expires_at.is_not(None))
        if expires_at is not None:
            extend = extend.where(Link.expires_at < expires_at)
        # SQLite loads expires_at without a timezone, so the ORM can't evaluate the WHERE in
        # Python against the session's objects; read the updated rows back instead.
        self._session.execute(
            extend.values(expires_at=expires_at), execution_options={"synchronize_session": "fetch"}
        )

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
