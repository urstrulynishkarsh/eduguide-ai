"""Counting rate limits in memory. No database needed."""

import pytest

from app.core import rate_limits
from app.core.errors import AuthenticationError, TooManyRequestsError
from app.core.rate_limits import Limit, MemoryCounter


async def test_counts_per_key():
    counter = MemoryCounter()
    assert [await counter.add("a", 60) for _ in range(3)] == [1, 2, 3]
    assert await counter.add("b", 60) == 1


async def test_refused_above_the_limit_with_the_wait():
    counter, limit = MemoryCounter(), Limit("test", 2, 15 * 60)
    await rate_limits.check(counter, limit, "someone@example.com")
    await rate_limits.check(counter, limit, "someone@example.com")
    with pytest.raises(TooManyRequestsError) as refused:
        await rate_limits.check(counter, limit, "someone@example.com")
    assert refused.value.code == "too_many_requests"
    assert 0 < refused.value.retry_after <= 15 * 60
    assert refused.value.headers == {"Retry-After": str(refused.value.retry_after)}
    await rate_limits.check(counter, limit, "someone.else@example.com")  # counted apart


async def test_a_daily_limit_says_so_and_waits_until_midnight_india_time():
    counter, limit = MemoryCounter(), Limit("test_day", 1, 24 * 60 * 60)
    await rate_limits.check(counter, limit, "family")
    with pytest.raises(TooManyRequestsError) as refused:
        await rate_limits.check(counter, limit, "family")
    assert refused.value.code == "daily_limit_reached"
    assert 0 < refused.value.retry_after <= 24 * 60 * 60


async def test_who_is_counted_is_never_stored_as_it_is():
    counter = MemoryCounter()
    await rate_limits.check(counter, Limit("test", 5, 60), "someone@example.com")
    (key,) = counter._counts
    assert "someone" not in key and key.startswith("eduguide:limit:test:")


async def test_only_failures_count_and_a_full_count_refuses_before_trying():
    counter, limit = MemoryCounter(), Limit("test_failures", 2, 15 * 60)
    async with rate_limits.failures(counter, (limit, "someone")):
        pass  # signed in: nothing counted
    for _ in range(2):
        with pytest.raises(AuthenticationError):
            async with rate_limits.failures(counter, (limit, "someone")):
                raise AuthenticationError()

    tried = False
    with pytest.raises(TooManyRequestsError):
        async with rate_limits.failures(counter, (limit, "someone")):
            tried = True
    assert not tried  # the password is not even looked at
