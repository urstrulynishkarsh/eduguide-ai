"""Rate limits on the routes: sign-in, sign-up, and the family's use of the AI (Step 12)."""

from httpx import AsyncClient

from app.core import rate_limits
from tests.api.helpers import API, add_child, error_code, register, start_child_session


async def test_sign_in_is_refused_after_ten_tries_for_one_email(client: AsyncClient):
    parent = await register(client)
    wrong = {"email": parent.email, "password": "not-the-password"}
    for _ in range(rate_limits.SIGN_IN_PER_EMAIL.times):
        assert (await client.post(f"{API}/auth/login", json=wrong)).status_code == 401

    # Even the right password waits now, also written another way.
    right = {"email": parent.email.upper(), "password": parent.password}
    refused = await client.post(f"{API}/auth/login", json=right)
    assert refused.status_code == 429
    assert error_code(refused) == "too_many_requests"
    assert 0 < int(refused.headers["Retry-After"]) <= 15 * 60
    assert refused.json()["error"]["details"] is None  # details are only ever the fields at fault

    other = await register(client)
    assert (
        await client.post(f"{API}/auth/login", json={"email": other.email, "password": other.password})
    ).status_code == 200


async def test_signing_in_that_works_is_never_counted(client: AsyncClient):
    parent = await register(client)
    right = {"email": parent.email, "password": parent.password}
    for _ in range(rate_limits.SIGN_IN_PER_EMAIL.times + 2):  # a family on many devices, a whole class
        assert (await client.post(f"{API}/auth/login", json=right)).status_code == 200


async def test_sign_up_is_limited_per_address(client: AsyncClient):
    for _ in range(rate_limits.SIGN_UP_PER_ADDRESS.times):
        await register(client)
    refused = await client.post(
        f"{API}/auth/register",
        json={
            "role": "parent",
            "full_name": "One More",
            "email": "one-more@example.com",
            "password": "Str0ng-Passw0rd",
        },
    )
    assert refused.status_code == 429


async def test_the_ai_limit_is_the_familys_also_in_child_mode(client: AsyncClient):
    parent = await register(client)
    child = await add_child(client, parent)
    child_headers = await start_child_session(client, parent, child["id"])
    body = {"question": "What is a fraction?"}

    # The AI is off in the tests (503), but every request still counts.
    for turn in range(rate_limits.AI_PER_MINUTE.times):
        if turn % 2:
            response = await client.post(f"{API}/learn/explain", json=body, headers=child_headers)
        else:
            chosen = {**body, "student_id": child["id"]}
            response = await client.post(f"{API}/learn/explain", json=chosen, headers=parent.headers)
        assert response.status_code == 503, response.text

    refused = await client.post(f"{API}/learn/explain", json=body, headers=child_headers)
    assert refused.status_code == 429
    assert error_code(refused) == "too_many_requests"

    other_family = await register(client)
    assert (
        await client.post(f"{API}/learn/explain", json=body, headers=other_family.headers)
    ).status_code != 429
