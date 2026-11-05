"""Rate limits on the routes: sign-in, sign-up, and the family's use of the AI (Step 12)."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import rate_limits
from tests.api.helpers import (
    API,
    add_child,
    bank,
    error_code,
    family_with_book,
    register,
    start_child_session,
)


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


async def test_marking_a_written_answer_counts_like_explain(client: AsyncClient, db_session: AsyncSession):
    parent, child, chapter = await family_with_book(client)
    for fmt in ("mcq", "short_answer"):
        await bank(db_session, parent, child, chapter, count=1, fmt=fmt)
    body = {"student_id": child["id"], "chapter_id": chapter["id"], "count": 2}
    session = (await client.post(f"{API}/practice/sessions", json=body, headers=parent.headers)).json()
    ids = {item["question"]["format"]: item["question"]["id"] for item in session["items"]}

    async def answer(fmt: str, **given: object) -> int:
        response = await client.post(
            f"{API}/practice/sessions/{session['id']}/answers",
            json={"question_id": ids[fmt], **given},
            headers=parent.headers,
        )
        return response.status_code

    # A choice is checked without the AI: trying again is free, however often.
    for _ in range(rate_limits.AI_PER_MINUTE.times + 1):
        assert await answer("mcq", option=1) == 200
    # Each written answer is marked by the AI (switched off here: 503), and counted.
    for _ in range(rate_limits.AI_PER_MINUTE.times):
        assert await answer("short_answer", text="Both sides stay equal.") == 503
    assert await answer("short_answer", text="Both sides stay equal.") == 429


async def test_submitting_a_test_with_written_answers_counts_once(
    client: AsyncClient, db_session: AsyncSession
):
    parent, child, chapter = await family_with_book(client)
    for fmt in ("mcq", "short_answer", "long_answer"):
        await bank(db_session, parent, child, chapter, count=1, fmt=fmt)
    body = {"student_id": child["id"], "kind": "chapter", "chapter_id": chapter["id"], "count": 3}
    test = (await client.post(f"{API}/mock-tests", json=body, headers=parent.headers)).json()
    sitting = (await client.post(f"{API}/mock-tests/{test['id']}/attempts", headers=parent.headers)).json()
    base = f"{API}/test-attempts/{sitting['id']}"
    for section in sitting["sections"]:
        for question in section["questions"]:
            given = {"option": 0} if question["format"] == "mcq" else {"text": "Both sides stay equal."}
            saved = await client.put(f"{base}/answers/{question['id']}", json=given, headers=parent.headers)
            assert saved.status_code == 204, saved.text
    explain = {"question": "What is a fraction?", "student_id": child["id"]}
    for _ in range(rate_limits.AI_PER_MINUTE.times - 1):
        await client.post(f"{API}/learn/explain", json=explain, headers=parent.headers)

    # Two written answers, one request: the minute's last (the AI is off: 503, nothing is marked).
    assert (await client.post(f"{base}/submit", headers=parent.headers)).status_code == 503
    refused = await client.post(f"{base}/submit", headers=parent.headers)
    assert refused.status_code == 429
    assert (await client.get(base, headers=parent.headers)).json()["status"] == "in_progress"
