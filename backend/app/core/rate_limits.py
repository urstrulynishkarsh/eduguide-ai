"""Rate limits: how often one address or one account may do something (docs/01 §1.10).

Counted in fixed windows (days start at midnight India time): in Redis when REDIS_URL is set, so
every API process shares the counts, else in this process's memory. The routes name their limits
(`limit_account`, `limit_address` in app/api/deps.py). An "account" is the family: child mode uses
the parent's account. Whom a count belongs to is stored hashed, never as an email or address.

These are starting values. Per address they are generous: a school or a coaching centre shares one.
"""

import hashlib
import logging
import math
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from functools import lru_cache
from typing import NoReturn, Protocol

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core import metrics
from app.core.config import get_settings
from app.core.errors import AuthenticationError, TooManyRequestsError
from app.core.redis import get_redis

logger = logging.getLogger(__name__)

_DAY = 24 * 60 * 60
_INDIA_OFFSET = 5 * 60 * 60 + 30 * 60  # UTC+05:30


@dataclass(frozen=True, slots=True)
class Limit:
    name: str
    times: int
    seconds: int

    @property
    def daily(self) -> bool:
        return self.seconds == _DAY


# Failed sign-ins only (`failures`): guessing one family's password, or many families' from one place.
SIGN_IN_PER_EMAIL = Limit("sign_in_email", 10, 15 * 60)
SIGN_IN_PER_ADDRESS = Limit("sign_in_address", 60, 15 * 60)
SIGN_UP_PER_ADDRESS = Limit("sign_up_address", 60, 60 * 60)
# Explain, the tutor and the assistant: each request is one or more calls to the AI.
AI_PER_MINUTE = Limit("ai_minute", 20, 60)
AI_PER_DAY = Limit("ai_day", 300, _DAY)
# Practice, tests and paper analyses: questions are written in the background.
PREPARE_PER_DAY = Limit("prepare_day", 60, _DAY)
# Files read in the background (an upload or a retry).
UPLOADS_PER_DAY = Limit("uploads_day", 100, _DAY)


class Counter(Protocol):
    async def add(self, key: str, seconds: int) -> int:
        """Adds one to `key` (forgotten after `seconds`) and returns its count."""

    async def get(self, key: str) -> int: ...


class RedisCounter:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def add(self, key: str, seconds: int) -> int:
        try:
            async with self._redis.pipeline(transaction=True) as pipe:
                count, _ = await pipe.incr(key).expire(key, seconds, nx=True).execute()
        except RedisError:
            # Redis is down: let the request through rather than refuse everyone.
            logger.warning("Rate limit not counted: Redis cannot be reached")
            return 0
        return count

    async def get(self, key: str) -> int:
        try:
            return int(await self._redis.get(key) or 0)
        except RedisError:
            logger.warning("Rate limit not checked: Redis cannot be reached")
            return 0


class MemoryCounter:
    """Keys name their window, so a key is never counted again once its time is up; old ones are
    dropped when there are many."""

    _PRUNE_ABOVE = 10_000

    def __init__(self) -> None:
        self._counts: dict[str, tuple[int, float]] = {}

    async def add(self, key: str, seconds: int) -> int:
        now = time.monotonic()
        if len(self._counts) > self._PRUNE_ABOVE:
            self._counts = {k: entry for k, entry in self._counts.items() if entry[1] > now}
        count, forget_at = self._counts.get(key, (0, now + seconds))
        self._counts[key] = (count + 1, forget_at)
        return count + 1

    async def get(self, key: str) -> int:
        return self._counts.get(key, (0, 0.0))[0]


@lru_cache
def get_counter() -> Counter:
    return RedisCounter(get_redis()) if get_settings().redis_url else MemoryCounter()


@dataclass(frozen=True, slots=True)
class _Window:
    key: str
    seconds_left: int


def _window(limit: Limit, who: str) -> _Window:
    now = time.time() + _INDIA_OFFSET
    window = int(now // limit.seconds)
    hashed = hashlib.sha256(who.encode()).hexdigest()[:32]
    return _Window(
        f"eduguide:limit:{limit.name}:{hashed}:{window}", math.ceil((window + 1) * limit.seconds - now)
    )


def _refuse(limit: Limit, window: _Window) -> NoReturn:
    metrics.RATE_LIMITED.labels(limit.name).inc()
    raise TooManyRequestsError(window.seconds_left, daily=limit.daily)


async def check(counter: Counter, limit: Limit, who: str) -> None:
    """Counts one more for `who`; refuses (429) once the window's count is above the limit."""
    window = _window(limit, who)
    if await counter.add(window.key, limit.seconds) > limit.times:
        _refuse(limit, window)


async def check_ai(counter: Counter, account: uuid.UUID) -> None:
    """A request seen to need the AI only once it is looked at (a written answer to mark): counted
    against the family's AI allowance, as `limit_account(AI_PER_MINUTE, AI_PER_DAY)` counts a route."""
    for limit in (AI_PER_MINUTE, AI_PER_DAY):
        await check(counter, limit, account.hex)


@asynccontextmanager
async def failures(counter: Counter, *counted: tuple[Limit, str]) -> AsyncIterator[None]:
    """For signing in: refuses (429) while any count is at its limit, before the password is even
    looked at; counts one more for each when the block fails to sign in. Signing in that works
    counts nothing."""
    windows = [(limit, _window(limit, who)) for limit, who in counted]
    for limit, window in windows:
        if await counter.get(window.key) >= limit.times:
            _refuse(limit, window)
    try:
        yield
    except AuthenticationError:
        for limit, window in windows:
            await counter.add(window.key, limit.seconds)
        raise
