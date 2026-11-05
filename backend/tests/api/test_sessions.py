"""Sessions: signing out stops every token of the session (Step 12)."""

from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuthSession
from tests.api.helpers import API, PASSWORD, add_child, bearer, error_code, register


async def _me(client: AsyncClient, token: str) -> int:
    return (await client.get(f"{API}/auth/me", headers=bearer(token))).status_code


async def _refresh(client: AsyncClient, refresh_token: str):
    return await client.post(f"{API}/auth/refresh", json={"refresh_token": refresh_token})


async def test_signing_out_stops_the_access_and_the_refresh_token(client: AsyncClient):
    parent = await register(client)
    tokens = parent.tokens
    assert await _me(client, tokens["access_token"]) == 200

    response = await client.post(f"{API}/auth/logout", json={"token": tokens["refresh_token"]})
    assert response.status_code == 204

    assert await _me(client, tokens["access_token"]) == 401
    refused = await _refresh(client, tokens["refresh_token"])
    assert refused.status_code == 401
    assert error_code(refused) == "invalid_token"


async def test_refreshed_tokens_belong_to_the_same_session(client: AsyncClient):
    parent = await register(client)
    renewed = (await _refresh(client, parent.tokens["refresh_token"])).json()
    assert await _me(client, renewed["access_token"]) == 200

    await client.post(f"{API}/auth/logout", json={"token": renewed["refresh_token"]})
    # The first sign-in's tokens are the same session: they stop too.
    assert await _me(client, parent.tokens["access_token"]) == 401
    assert (await _refresh(client, parent.tokens["refresh_token"])).status_code == 401


async def test_signing_out_on_one_device_keeps_the_others(client: AsyncClient):
    parent = await register(client)
    login = await client.post(f"{API}/auth/login", json={"email": parent.email, "password": PASSWORD})
    other_device = login.json()["tokens"]

    await client.post(f"{API}/auth/logout", json={"token": parent.tokens["refresh_token"]})
    assert await _me(client, other_device["access_token"]) == 200


async def test_leaving_child_mode_ends_the_child_session_only(client: AsyncClient):
    parent = await register(client)
    child = await add_child(client, parent)
    response = await client.post(f"{API}/students/{child['id']}/session", headers=parent.headers)
    child_token = response.json()["access_token"]
    assert await _me(client, child_token) == 200

    # Child mode has no refresh token: its access token is what the frontend sends.
    await client.post(f"{API}/auth/logout", json={"token": child_token})
    assert await _me(client, child_token) == 401
    assert await _me(client, parent.tokens["access_token"]) == 200


async def test_signing_out_twice_or_with_nonsense_is_harmless(client: AsyncClient):
    parent = await register(client)
    for token in [parent.tokens["refresh_token"], parent.tokens["refresh_token"], "not-a-token"]:
        assert (await client.post(f"{API}/auth/logout", json={"token": token})).status_code == 204
    empty = await client.post(f"{API}/auth/logout", json={"token": ""})
    assert empty.status_code == 422


async def test_old_sessions_are_removed_at_the_next_sign_in(client: AsyncClient, db_session: AsyncSession):
    parent = await register(client)
    await client.post(f"{API}/auth/logout", json={"token": parent.tokens["refresh_token"]})
    await client.post(f"{API}/auth/login", json={"email": parent.email, "password": PASSWORD})

    sessions = await db_session.scalar(
        select(func.count()).select_from(AuthSession).where(AuthSession.user_id == parent.user["id"])
    )
    assert sessions == 1  # the new one; the signed-out one is gone
