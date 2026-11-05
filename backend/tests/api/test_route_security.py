"""Every route needs a sign-in, except a short public list (Step 12, docs/08-security-review.md).

A new route is checked here without anyone remembering to: called with no token, it must answer 401.
"""

import re

from httpx import AsyncClient

from app.main import app

# Open to everyone, on purpose: health checks, signing up and in, and the sign-up forms' options.
PUBLIC = {
    "GET /health",
    "GET /health/ready",
    "POST /api/v1/auth/register",
    "POST /api/v1/auth/login",
    "POST /api/v1/auth/refresh",
    "POST /api/v1/auth/logout",
    "GET /api/v1/meta/options",
    "GET /api/v1/meta/classes/{class_level}",
}
_ANY_ID = "00000000-0000-0000-0000-000000000000"


def _routes() -> list[tuple[str, str]]:
    return [
        (method.upper(), path) for path, operations in app.openapi()["paths"].items() for method in operations
    ]


async def test_every_route_but_the_public_ones_needs_a_sign_in(client: AsyncClient):
    routes = _routes()
    assert len(routes) > 50  # the whole API is seen
    open_routes = set()
    for method, path in routes:
        url = re.sub(r"\{[^}]+\}", lambda part: "class_7" if part[0] == "{class_level}" else _ANY_ID, path)
        response = await client.request(method, url, json={})
        if response.status_code != 401:
            open_routes.add(f"{method} {path}")
    assert open_routes == PUBLIC
