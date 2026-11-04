"""Streaks, XP and badges: earned while practising and taking tests, never taken away."""

from datetime import timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import rewards
from tests.api.helpers import API, bank, error_code, family_with_book, register, start_child_session
from tests.api.test_adaptive import _practise
from tests.api.test_mock_tests import _chapter_test, _fill_bank, _ids


async def _rewards(client: AsyncClient, headers: dict, child: dict) -> dict:
    response = await client.get(f"{API}/students/{child['id']}/rewards", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def _earned(summary: dict) -> set[str]:
    return {badge["code"] for badge in summary["badges"] if badge["earned_at"]}


async def test_practice_earns_xp_the_days_goal_and_badges_once(client: AsyncClient, db_session: AsyncSession):
    parent, child, chapter = await family_with_book(client)  # Class 7: the day's goal is 10 answers
    await bank(db_session, parent, child, chapter, count=10)
    body = {"student_id": child["id"], "topic_id": chapter["topics"][-1]["id"], "count": 5}

    first = await _practise(client, parent.headers, body, [True] * 5)
    gains = [answer["rewards"] for answer in first["answers"]]
    assert [gain["xp"] for gain in gains] == [10, 10, 10, 10, 10 + 20]  # the last one finishes it
    # A perfect first practice, and five right answers make the topic strong.
    assert gains[-1]["badges"] == ["first_practice", "perfect_practice", "topic_mastered"]

    # Answering again earns nothing: only first answers count.
    again = await client.post(
        f"{API}/practice/sessions/{first['id']}/answers",
        json={"question_id": first["items"][0]["question"]["id"], "option": 0},
        headers=parent.headers,
    )
    assert again.json()["rewards"] == {"xp": 0, "badges": []}

    second = await _practise(client, parent.headers, body, [False] * 5)
    assert [answer["rewards"]["xp"] for answer in second["answers"]] == [2, 2, 2, 2, 2 + 20 + 10]  # + goal

    summary = await _rewards(client, parent.headers, child)
    assert (summary["xp"], summary["level"], summary["level_xp"], summary["level_size"]) == (110, 2, 10, 150)
    assert (summary["streak"], summary["longest_streak"], summary["today"]) == (
        1,
        1,
        {"answered": 10, "goal": 10},
    )
    assert _earned(summary) == {"first_practice", "perfect_practice", "topic_mastered"}
    assert [badge["code"] for badge in summary["badges"]][3:] == [
        code for code in rewards.BADGES if code not in _earned(summary)
    ]
    board = (await client.get(f"{API}/students/{child['id']}/dashboard", headers=parent.headers)).json()
    assert board["rewards"] == summary


async def test_a_streak_grows_day_by_day_and_is_lost_after_a_missed_day(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    parent, child, chapter = await family_with_book(client)
    await bank(db_session, parent, child, chapter, count=4)
    body = {"student_id": child["id"], "topic_id": chapter["topics"][-1]["id"], "count": 1}
    day = rewards.today()

    for offset in (0, 1, 2):
        monkeypatch.setattr(rewards, "today", lambda offset=offset: day + timedelta(days=offset))
        await _practise(client, parent.headers, body, [True])
    summary = await _rewards(client, parent.headers, child)
    assert (summary["streak"], summary["today"]["answered"]) == (3, 1)
    assert "streak_3" in _earned(summary)

    monkeypatch.setattr(rewards, "today", lambda: day + timedelta(days=4))  # a day without answers
    assert (await _rewards(client, parent.headers, child))["streak"] == 0
    await _practise(client, parent.headers, body, [False])
    summary = await _rewards(client, parent.headers, child)
    assert (summary["streak"], summary["longest_streak"]) == (1, 3)


async def test_a_submitted_test_earns_xp_for_its_answers(client: AsyncClient, db_session: AsyncSession):
    parent, child, chapter = await family_with_book(client)
    await _fill_bank(db_session, parent, child, chapter, short_answer=2, long_answer=1)
    test = await _chapter_test(client, parent, child, chapter)
    (mcq1, mcq2, mcq3), *_ = (_ids(section) for section in test["sections"])
    attempt = (await client.post(f"{API}/mock-tests/{test['id']}/attempts", headers=parent.headers)).json()
    base = f"{API}/test-attempts/{attempt['id']}"
    for question, option in ((mcq1, 0), (mcq2, 0), (mcq3, 1)):  # the written ones are left out
        await client.put(f"{base}/answers/{question}", json={"option": option}, headers=parent.headers)
    assert (await client.post(f"{base}/submit", headers=parent.headers)).status_code == 200
    await client.post(f"{base}/submit", headers=parent.headers)  # submitting again counts nothing

    summary = await _rewards(client, parent.headers, child)
    assert summary["xp"] == 3 * 2 + 2 * 8 + 20
    assert _earned(summary) == {"first_test"}


async def test_only_the_family_sees_a_learners_rewards(client: AsyncClient):
    parent, child, _ = await family_with_book(client)
    child_mode = await start_child_session(client, parent, child["id"])
    assert (await _rewards(client, child_mode, child))["xp"] == 0  # nothing yet, every badge to earn
    stranger = await register(client)
    refused = await client.get(f"{API}/students/{child['id']}/rewards", headers=stranger.headers)
    assert refused.status_code == 404 and error_code(refused) == "student_not_found"
