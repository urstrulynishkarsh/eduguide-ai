from httpx import AsyncClient


async def test_health(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_ready_checks_the_database(client: AsyncClient):
    response = await client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "up"}


async def test_every_response_carries_a_request_id(client: AsyncClient):
    response = await client.get("/health")
    assert len(response.headers["X-Request-ID"]) >= 8

    echoed = await client.get("/health", headers={"X-Request-ID": "my-trace-id-123"})
    assert echoed.headers["X-Request-ID"] == "my-trace-id-123"

    unsafe = await client.get("/health", headers={"X-Request-ID": "bad id\twith spaces"})
    assert unsafe.headers["X-Request-ID"] != "bad id\twith spaces"


async def test_unknown_route_uses_the_standard_error_format(client: AsyncClient):
    response = await client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


async def test_api_documentation_is_generated(client: AsyncClient):
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/auth/register" in paths
    assert "/api/v1/students" in paths
