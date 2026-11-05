"""The Redis parts (the job queue, the worker, the rate limits) against a real Redis.

They need Redis (`docker compose up -d` starts it) and use database 15, emptied around each test.
"""

import os
from collections.abc import AsyncIterator

import pytest
from redis.asyncio import Redis
from redis.exceptions import ConnectionError as RedisConnectionError

REDIS_TEST_URL = os.environ.get("REDIS_TEST_URL", "redis://localhost:6379/15")


@pytest.fixture
async def redis() -> AsyncIterator[Redis]:
    client = Redis.from_url(REDIS_TEST_URL)
    try:
        await client.flushdb()
    except RedisConnectionError as exc:
        pytest.exit(
            f"Cannot reach Redis at {REDIS_TEST_URL}. Start it with `docker compose up -d` from the "
            f"project root. ({exc})",
            returncode=2,
        )
    yield client
    await client.flushdb()
    await client.aclose()
