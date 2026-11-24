from datetime import UTC, datetime, timedelta

import pytest

from shorten_me.expiry import InvalidExpiry, expiry_in_utc


def test_expiry_in_the_past_is_rejected():
    now = datetime(2026, 1, 1, tzinfo=UTC)
    with pytest.raises(InvalidExpiry):
        expiry_in_utc(now - timedelta(days=1), now)
