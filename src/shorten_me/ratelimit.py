"""Limit how often each client can make a request."""

from collections.abc import Callable
from threading import Lock


class RateLimited(Exception):
    """Raised when a client has no requests left; `retry_after` is in seconds."""

    def __init__(self, retry_after: float) -> None:
        super().__init__(f"retry after {retry_after:.1f}s")
        self.retry_after = retry_after


class RateLimiter:
    """Allow each client a burst of `limit` requests, refilled evenly over `period` seconds."""

    def __init__(self, limit: int, period: float, clock: Callable[[], float]) -> None:
        if limit < 1 or period <= 0:
            raise ValueError(f"limit and period must be positive, got {limit} and {period}")
        self._limit = limit
        self._period = period
        self._rate = limit / period
        self._clock = clock
        self._buckets: dict[str, tuple[float, float]] = {}
        self._next_prune = clock() + period
        self._lock = Lock()

    def take(self, client: str) -> None:
        """Use up one of the client's requests, or raise `RateLimited` if none is left."""
        now = self._clock()
        with self._lock:
            if now >= self._next_prune:
                self._forget_full_buckets(now)
            left = self._left(client, now)
            if left < 1:
                raise RateLimited((1 - left) / self._rate)
            self._buckets[client] = (left - 1, now)

    def _left(self, client: str, now: float) -> float:
        left, updated = self._buckets.get(client, (self._limit, now))
        return min(self._limit, left + (now - updated) * self._rate)

    def _forget_full_buckets(self, now: float) -> None:
        self._buckets = {
            client: bucket
            for client, bucket in self._buckets.items()
            if self._left(client, now) < self._limit
        }
        self._next_prune = now + self._period
