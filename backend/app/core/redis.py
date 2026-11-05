"""The one Redis connection of a process (REDIS_URL): the job queue, the rate limits, the readiness check."""

from functools import lru_cache

from redis.asyncio import Redis

from app.core.config import get_settings


@lru_cache
def get_redis() -> Redis:
    return Redis.from_url(get_settings().redis_url)
