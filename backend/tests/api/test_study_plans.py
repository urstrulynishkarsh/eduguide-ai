"""The study planner: tasks from today to the exam, planned again each morning from what the learner
knows, ticked off by practice and tests.

"Tomorrow" is reached by moving the planner's day forward (recommendations.today, India time).
"""

from datetime import date, timedelta
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.adaptive_learning import recommendations
from tests.api.helpers import (
    API,
    add_child,
    bank,
    error_code,
    family_with_book,
    reason,
    register,
    start_child_session,
)

TODAY = recommendations.today()


async def _plan(client: AsyncClient, headers: dict, child: dict, days: int, **settings: Any):
    body = {"student_id": child["id"], "exam_date": str(TODAY + timedelta(days=days)), **settings}
    return await client.post(f"{API}/study-plans", json=body, headers=headers)


def _tasks(plan: dict) -> list[tuple[str, str, str | None, str | None]]:
    """(day from today, kind, chapter, topic) of every task."""
    return [
        (f"+{(date.fromisoformat(item['day']) - TODAY).days}", item["kind"], item["chapter"], item["topic"])
        for day in plan["days"]
        for item in day["items"]
    ]


async def _practise(client: AsyncClient, headers: dict, body: dict, results: list[bool]) -> None:
    session = (await client.post(f"{API}/practice/sessions", json=body, headers=headers)).json()
    assert session["status"] == "ready", session
    for item, right in zip(session["items"], results, strict=True):
        await client.post(
            f"{API}/practice/sessions/{session['id']}/answers",
            json={"question_id": item["question"]["id"], "option": 0 if right else 1},
            headers=headers,
        )


async def test_a_plan_from_today_to_the_exam(client: AsyncClient):
    parent, child, _ = await family_with_book(client)

    response = await _plan(client, parent.headers, child, 10, daily_minutes=40)

    assert response.status_code == 201, response.text
    plan = response.json()
    first, second = "Chapter 1 Rational Numbers", "Chapter 2 Linear Equations in One Variable"
    # Learn and practise each new chapter, then practise them in turn (4 practices each to reach 80%),
    # spread over the days within 40 minutes a day; the book's practice test on the last day.
    assert _tasks(plan) == [
        ("+0", "learn", first, None),
        ("+0", "practice", first, None),
        ("+1", "learn", second, None),
        ("+2", "practice", second, None),
        *[(f"+{day}", "practice", (first, second)[day % 2 == 0], None) for day in range(3, 9)],
        ("+9", "test", None, None),
    ]
    assert (plan["status"], plan["days_left"], plan["unscheduled"], plan["total"], plan["done"]) == (
        "active",
        10,
        0,
        11,
        0,
    )
    learn, practice, *_, test = (item for day in plan["days"] for item in day["items"])
    assert (learn["minutes"], reason(learn)) == (15, {"code": "learn_first"})
    assert learn["revise"]["question"] == first and learn["practice"] is None
    assert practice["practice"]["chapter_id"] == practice["chapter_id"]
    assert practice["practice"]["difficulty"] == "mixed"
    assert test["test"] | {"student_id": None} == {
        "student_id": None,
        "kind": "practice",  # Class 7 has no full mock tests
        "book_id": test["book_id"],
        "chapter_id": None,
        "topic_id": None,
        "exercise_id": None,
        "count": None,
        "difficulty": "mixed",
        "duration_minutes": None,
        "language": None,
    }
    assert (test["minutes"], reason(test)) == (45, {"code": "practice_test"})
    again = await client.get(f"{API}/students/{child['id']}/study-plan", headers=parent.headers)
    assert again.json() == plan


async def test_each_morning_the_rest_is_planned_again_from_what_the_learner_knows(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    parent, child, chapter = await family_with_book(client)
    plan = (
        await _plan(client, parent.headers, child, 3, chapter_ids=[chapter["id"]], daily_minutes=90)
    ).json()
    assert [(day, kind) for day, kind, _, _ in _tasks(plan)] == [
        ("+0", "learn"),
        ("+0", "practice"),
        ("+1", "practice"),
        ("+1", "practice"),
        ("+2", "practice"),
        ("+2", "test"),
    ]

    # Today the child skips the plan and does badly on one topic.
    await bank(db_session, parent, child, chapter, count=5)
    topic = chapter["topics"][-1]
    body = {"student_id": child["id"], "topic_id": topic["id"], "count": 5}
    await _practise(client, parent.headers, body, [True, False, False, False, False])

    monkeypatch.setattr(recommendations, "today", lambda: TODAY + timedelta(days=1))
    plan = (await client.get(f"{API}/students/{child['id']}/study-plan", headers=parent.headers)).json()

    chapter_name = "Chapter 2 Linear Equations in One Variable"
    assert _tasks(plan) == [
        ("+0", "learn", chapter_name, None),  # yesterday's two, missed
        ("+0", "practice", chapter_name, None),
        ("+1", "learn", chapter_name, "2.2 Solving Equations"),  # the weak topic first
        ("+1", "practice", chapter_name, "2.2 Solving Equations"),
        ("+1", "practice", chapter_name, None),
        ("+2", "practice", chapter_name, None),
        ("+2", "practice", chapter_name, None),
        ("+2", "test", None, None),
    ]
    items = [item for day in plan["days"] for item in day["items"]]
    assert [item["status"] for item in items] == ["missed"] * 2 + ["pending"] * 6
    assert (plan["missed"], plan["planned_on"]) == (2, str(TODAY + timedelta(days=1)))
    assert reason(items[2]) == {"code": "revise", "accuracy": 0.2, "answers": 5}
    assert {item["difficulty"] for item in items[3:7]} == {"easy"}  # the level went down

    # Doing the task as planned ticks it off.
    await bank(db_session, parent, child, chapter, count=10, difficulty="easy")
    await _practise(client, parent.headers, items[3]["practice"], [True] * 10)
    plan = (await client.get(f"{API}/students/{child['id']}/study-plan", headers=parent.headers)).json()
    assert [item["status"] for day in plan["days"] for item in day["items"]][3] == "done"
    assert plan["done"] == 1


async def test_tasks_are_ticked_off_by_hand_or_by_taking_the_test(
    client: AsyncClient, db_session: AsyncSession
):
    parent, child, chapter = await family_with_book(client)
    plan = (
        await _plan(client, parent.headers, child, 1, chapter_ids=[chapter["id"]], daily_minutes=120)
    ).json()
    learn, *_, test = plan["days"][0]["items"]
    child_mode = await start_child_session(client, parent, child["id"])

    for status in ("done", "skipped", "pending", "done"):
        ticked = await client.patch(
            f"{API}/study-plan-items/{learn['id']}", json={"status": status}, headers=child_mode
        )
        assert (ticked.status_code, ticked.json()["status"]) == (200, status)
    refused = await client.patch(
        f"{API}/study-plan-items/{learn['id']}", json={"status": "missed"}, headers=child_mode
    )
    assert refused.status_code == 422

    await bank(db_session, parent, child, chapter, count=5)
    await bank(db_session, parent, child, chapter, count=3, fmt="short_answer")
    await bank(db_session, parent, child, chapter, count=2, fmt="long_answer")
    made = await client.post(f"{API}/mock-tests", json=test["test"], headers=child_mode)
    assert made.json()["status"] == "ready", made.text
    attempt = (await client.post(f"{API}/mock-tests/{made.json()['id']}/attempts", headers=child_mode)).json()
    await client.post(f"{API}/test-attempts/{attempt['id']}/submit", headers=child_mode)

    plan = (await client.get(f"{API}/students/{child['id']}/study-plan", headers=child_mode)).json()
    statuses = [item["status"] for item in plan["days"][0]["items"]]
    assert statuses == ["done", "pending", "pending", "pending", "done"]


async def test_too_little_time_is_reported_and_the_youngest_get_no_tests(client: AsyncClient):
    parent, child, _ = await family_with_book(client)
    plan = (await _plan(client, parent.headers, child, 1, daily_minutes=10)).json()
    assert [kind for _, kind, _, _ in _tasks(plan)] == ["test"]  # the test fills the only day
    assert plan["unscheduled"] == 10

    little, young, _ = await family_with_book(client, class_level="ukg")
    plan = (await _plan(client, little.headers, young, 5)).json()
    assert [kind for _, kind, _, _ in _tasks(plan)] == ["learn"] + ["practice"] * 4  # no test


async def test_a_new_plan_replaces_the_old_and_only_the_family_sees_it(client: AsyncClient):
    parent, child, chapter = await family_with_book(client)
    child_mode = await start_child_session(client, parent, child["id"])
    stranger = await register(client)
    theirs = await add_child(client, stranger, class_level="class_7")

    async def refused(response) -> tuple[int, str]:
        return response.status_code, error_code(response)

    assert await refused(await _plan(client, parent.headers, child, 0)) == (422, "validation_error")
    assert await refused(await _plan(client, parent.headers, child, 400)) == (422, "validation_error")
    assert await refused(await _plan(client, child_mode, child, 5)) == (403, "parent_required")
    borrowed = await _plan(client, stranger.headers, theirs, 5, chapter_ids=[chapter["id"]])
    assert await refused(borrowed) == (404, "chapter_not_found")

    old = (await _plan(client, parent.headers, child, 5)).json()
    new = (await _plan(client, parent.headers, child, 8, daily_minutes=45)).json()
    current = (await client.get(f"{API}/students/{child['id']}/study-plan", headers=child_mode)).json()
    assert (current["id"], current["exam_date"], current["daily_minutes"]) == (
        new["id"],
        str(TODAY + timedelta(days=8)),
        45,
    )
    task = old["days"][0]["items"][0]["id"]
    assert await refused(
        await client.patch(f"{API}/study-plan-items/{task}", json={"status": "done"}, headers=parent.headers)
    ) == (404, "plan_item_not_found")  # went with the old plan

    task = new["days"][0]["items"][0]["id"]
    assert await refused(
        await client.patch(
            f"{API}/study-plan-items/{task}", json={"status": "done"}, headers=stranger.headers
        )
    ) == (404, "plan_item_not_found")
    assert await refused(
        await client.get(f"{API}/students/{child['id']}/study-plan", headers=stranger.headers)
    ) == (404, "student_not_found")
    assert await refused(await client.delete(f"{API}/study-plans/{new['id']}", headers=stranger.headers)) == (
        404,
        "study_plan_not_found",
    )
    assert await refused(await client.delete(f"{API}/study-plans/{new['id']}", headers=child_mode)) == (
        403,
        "parent_required",
    )
    assert (await client.delete(f"{API}/study-plans/{new['id']}", headers=parent.headers)).status_code == 204
    assert await refused(
        await client.get(f"{API}/students/{child['id']}/study-plan", headers=parent.headers)
    ) == (
        404,
        "study_plan_not_found",
    )
