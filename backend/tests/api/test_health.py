import json
import logging

from httpx import AsyncClient
from prometheus_client import REGISTRY

from app import main
from app.core.config import Settings
from app.core.logging import JsonFormatter


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


async def test_answers_carry_the_security_headers(client: AsyncClient):
    response = await client.get("/health")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Content-Security-Policy"] == "default-src 'none'; frame-ancestors 'none'"
    assert "Strict-Transport-Security" not in response.headers  # production only
    # The API docs page loads its scripts from a CDN (and is not served in production).
    assert "Content-Security-Policy" not in (await client.get("/docs")).headers


def test_production_serves_no_api_docs(monkeypatch):
    production = Settings(
        _env_file=None, jwt_secret_key="s" * 48, environment="production", redis_url="redis://redis:6379/0"
    )
    monkeypatch.setattr(main, "get_settings", lambda: production)
    app = main.create_app()
    assert app.docs_url is None and app.redoc_url is None and app.openapi_url is None


async def test_requests_are_counted_by_route_pattern(client: AsyncClient):
    def count() -> float:
        labels = {"method": "GET", "route": "/api/v1/books/{book_id}", "status": "401"}
        return REGISTRY.get_sample_value("eduguide_http_requests_total", labels) or 0

    before = count()
    await client.get("/api/v1/books/00000000-0000-0000-0000-000000000000")
    assert count() == before + 1


def test_json_logs_are_one_object_per_line():
    record = logging.LogRecord("app.test", logging.INFO, __file__, 1, "Read %d pages", (12,), None)
    record.request_id = "abc123"
    line = json.loads(JsonFormatter().format(record))
    assert line["message"] == "Read 12 pages"
    assert line["level"] == "INFO" and line["request_id"] == "abc123" and line["logger"] == "app.test"
