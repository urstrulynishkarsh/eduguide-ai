"""The parent PIN: set before the first hand-over, the only way out of child mode (docs/08 §8.3)."""

import pytest
from httpx import AsyncClient

from app.core import rate_limits
from app.core.rate_limits import Limit
from tests.api.helpers import (
    API,
    PIN,
    add_child,
    bearer,
    error_code,
    hand_over,
    register,
    set_pin,
    start_child_session,
)


async def _leave(client: AsyncClient, child_token: str, pin: str):
    return await client.post(f"{API}/auth/child-mode/leave", json={"pin": pin}, headers=bearer(child_token))


async def _me(client: AsyncClient, token: str):
    return await client.get(f"{API}/auth/me", headers=bearer(token))


async def test_child_mode_needs_a_parent_pin_first(client: AsyncClient):
    parent = await register(client)
    child = await add_child(client, parent)
    url = f"{API}/students/{child['id']}/session"

    refused = await client.post(url, headers=parent.headers)
    assert refused.status_code == 409
    assert error_code(refused) == "pin_not_set"
    assert (await _me(client, parent.tokens["access_token"])).json()["pin_set"] is False

    wrong = await client.put(
        f"{API}/auth/pin", json={"password": "not-the-password", "pin": PIN}, headers=parent.headers
    )
    assert wrong.status_code == 401
    assert error_code(wrong) == "wrong_password"
    for pin in ["123", "12345", "12a4", "١٢٣٤", ""]:  # the last but one: Arabic-Indic digits
        invalid = await client.put(
            f"{API}/auth/pin", json={"password": parent.password, "pin": pin}, headers=parent.headers
        )
        assert invalid.status_code == 422, pin
        assert invalid.json()["error"]["details"] == [{"field": "pin", "message": "The PIN is 4 digits."}]

    await set_pin(client, parent)
    assert (await _me(client, parent.tokens["access_token"])).json()["pin_set"] is True
    assert (await client.post(url, headers=parent.headers)).status_code == 200


async def test_only_the_parent_sets_the_pin(client: AsyncClient):
    parent = await register(client)
    child = await add_child(client, parent)
    child_mode = await start_child_session(client, parent, child["id"])
    student = await register(client, role="student")
    body = {"password": parent.password, "pin": "1357"}

    for headers in [child_mode, student.headers]:
        refused = await client.put(f"{API}/auth/pin", json=body, headers=headers)
        assert refused.status_code == 403
        assert error_code(refused) == "parent_required"
    assert (await _me(client, student.tokens["access_token"])).json()["pin_set"] is False


async def test_the_pin_ends_child_mode_and_signs_the_parent_in(client: AsyncClient):
    parent = await register(client)
    child = await add_child(client, parent)
    child_mode = await hand_over(client, parent, child["id"])
    child_token = child_mode["access_token"]

    wrong = await _leave(client, child_token, "1111")
    assert wrong.status_code == 401
    assert error_code(wrong) == "wrong_pin"
    assert (await _me(client, child_token)).status_code == 200  # still in child mode

    left = await _leave(client, child_token, PIN)
    assert left.status_code == 200
    tokens = left.json()["tokens"]
    me = (await _me(client, tokens["access_token"])).json()
    assert me["active_role"] == "parent"
    assert me["active_student"] is None

    # Child mode is over: none of its tokens work.
    assert (await _me(client, child_token)).status_code == 401
    renewed = await client.post(f"{API}/auth/refresh", json={"refresh_token": child_mode["refresh_token"]})
    assert renewed.status_code == 401


async def test_child_mode_is_renewed_as_that_child_only(client: AsyncClient):
    parent = await register(client)
    aarav = await add_child(client, parent)
    await add_child(client, parent, class_level="ukg")
    child_mode = await hand_over(client, parent, aarav["id"])

    renewed = await client.post(f"{API}/auth/refresh", json={"refresh_token": child_mode["refresh_token"]})
    assert renewed.status_code == 200
    headers = bearer(renewed.json()["access_token"])
    me = (await client.get(f"{API}/auth/me", headers=headers)).json()
    assert me["active_role"] == "student"
    assert me["active_student"]["id"] == aarav["id"]
    assert [student["id"] for student in (await client.get(f"{API}/students", headers=headers)).json()] == [
        aarav["id"]
    ]
    assert (await client.post(f"{API}/students/{aarav['id']}/session", headers=headers)).status_code == 403

    # Removing the child ends their child mode, renewals too.
    await client.delete(f"{API}/students/{aarav['id']}", headers=parent.headers)
    gone = await client.post(f"{API}/auth/refresh", json={"refresh_token": child_mode["refresh_token"]})
    assert gone.status_code == 401


async def test_child_mode_is_not_signed_out_without_the_pin(client: AsyncClient):
    parent = await register(client)
    child = await add_child(client, parent)
    child_mode = await hand_over(client, parent, child["id"])

    for token in [child_mode["access_token"], child_mode["refresh_token"]]:
        refused = await client.post(f"{API}/auth/logout", json={"token": token})
        assert refused.status_code == 403
        assert error_code(refused) == "pin_required"
    assert (await _me(client, child_mode["access_token"])).status_code == 200

    # Once left with the PIN, signing it out again is harmless.
    await _leave(client, child_mode["access_token"], PIN)
    gone = await client.post(f"{API}/auth/logout", json={"token": child_mode["refresh_token"]})
    assert gone.status_code == 204


async def test_only_child_mode_is_left(client: AsyncClient):
    parent = await register(client)
    await set_pin(client, parent)
    student = await register(client, role="student")

    for account in [parent, student]:
        refused = await _leave(client, account.tokens["access_token"], PIN)
        assert refused.status_code == 403
        assert error_code(refused) == "not_child_mode"


async def test_wrong_pins_are_limited_per_family(client: AsyncClient):
    parent = await register(client)
    child = await add_child(client, parent)
    child_token = (await hand_over(client, parent, child["id"]))["access_token"]
    for _ in range(rate_limits.PIN_PER_ACCOUNT.times):
        assert (await _leave(client, child_token, "0000")).status_code == 401

    # Even the right PIN waits now.
    refused = await _leave(client, child_token, PIN)
    assert refused.status_code == 429
    assert error_code(refused) == "too_many_requests"
    assert 0 < int(refused.headers["Retry-After"]) <= 15 * 60

    other = await register(client)
    other_child = await add_child(client, other)
    other_token = (await hand_over(client, other, other_child["id"]))["access_token"]
    assert (await _leave(client, other_token, PIN)).status_code == 200


async def test_wrong_pins_are_limited_per_day(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(rate_limits, "PIN_PER_ACCOUNT", Limit("pin_account", 1000, 15 * 60))
    parent = await register(client)
    child = await add_child(client, parent)
    child_token = (await hand_over(client, parent, child["id"]))["access_token"]
    for _ in range(rate_limits.PIN_PER_DAY.times):
        assert (await _leave(client, child_token, "0000")).status_code == 401

    refused = await _leave(client, child_token, PIN)
    assert refused.status_code == 429
    assert error_code(refused) == "daily_limit_reached"
