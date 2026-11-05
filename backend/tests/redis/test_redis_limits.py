"""Rate limits counted in Redis, and the readiness check with Redis (Step 12)."""

from httpx import AsyncClient
from redis.asyncio import Redis

from app.api import health
from app.core.rate_limits import RedisCounter


async def test_counts_are_kept_in_redis_and_forgotten(redis: Redis):
    counter = RedisCounter(redis)
    assert [await counter.add("eduguide:limit:test", 60) for _ in range(3)] == [1, 2, 3]
    assert 0 < await redis.ttl("eduguide:limit:test") <= 60


async def test_without_redis_requests_are_let_through():
    unreachable = Redis.from_url("redis://localhost:1/0")
    assert await RedisCounter(unreachable).add("eduguide:limit:test", 60) == 0
    await unreachable.aclose()


async def test_ready_checks_redis_when_it_is_used(client: AsyncClient, redis: Redis, monkeypatch):
    class WithRedis:
        redis_url = "redis://test"

    monkeypatch.setattr(health, "get_settings", WithRedis)
    monkeypatch.setattr(health, "get_redis", lambda: redis)
    response = await client.get("/health/ready")
    assert response.json() == {"status": "ready", "database": "up", "redis": "up"}

    unreachable = Redis.from_url("redis://localhost:1/0")
    monkeypatch.setattr(health, "get_redis", lambda: unreachable)
    response = await client.get("/health/ready")
    assert response.status_code == 503
    assert response.json()["redis"] == "down"
    await unreachable.aclose()
