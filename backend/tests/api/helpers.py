"""Small helpers that keep the API tests readable."""

import uuid
from dataclasses import dataclass
from typing import Any

from httpx import AsyncClient

API = "/api/v1"
PASSWORD = "Str0ng-Passw0rd"


@dataclass
class Account:
    user: dict[str, Any]
    tokens: dict[str, Any]
    email: str
    password: str

    @property
    def headers(self) -> dict[str, str]:
        return bearer(self.tokens["access_token"])


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def register(client: AsyncClient, role: str = "parent", **overrides: Any) -> Account:
    payload = {
        "role": role,
        "full_name": "Test User",
        "email": f"user-{uuid.uuid4().hex[:12]}@example.com",
        "password": PASSWORD,
        **overrides,
    }
    response = await client.post(f"{API}/auth/register", json=payload)
    assert response.status_code == 201, response.text
    body = response.json()
    return Account(
        user=body["user"], tokens=body["tokens"], email=payload["email"], password=payload["password"]
    )


def child_payload(**profile_overrides: Any) -> dict[str, Any]:
    """Aarav, Class 7, CBSE - the example child from the product spec."""
    return {
        "name": "Aarav",
        "age": 12,
        "profile": {
            "class_level": "class_7",
            "board": "cbse",
            "medium": "en",
            "primary_language": "hinglish",
            "subjects": ["Mathematics", "Science"],
            **profile_overrides,
        },
    }


async def add_child(client: AsyncClient, parent: Account, **profile_overrides: Any) -> dict[str, Any]:
    response = await client.post(
        f"{API}/students", json=child_payload(**profile_overrides), headers=parent.headers
    )
    assert response.status_code == 201, response.text
    return response.json()


async def start_child_session(client: AsyncClient, parent: Account, student_id: str) -> dict[str, str]:
    """Returns the headers of a child-mode session."""
    response = await client.post(f"{API}/students/{student_id}/session", headers=parent.headers)
    assert response.status_code == 200, response.text
    return bearer(response.json()["access_token"])


def error_code(response: Any) -> str:
    return response.json()["error"]["code"]
