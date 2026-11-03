"""The parent dashboard in one call: the week, strong and weak areas, what to do next, tests, the plan."""

from datetime import timedelta

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.adaptive_learning import recommendations
from tests.api.helpers import (
    API,
    add_child,
    bank,
    error_code,
    family_with_book,
    register,
    start_child_session,
)


async def _practise(client: AsyncClient, headers: dict, body: dict, results: list[bool]) -> None:
    session = (await client.post(f"{API}/practice/sessions", json=body, headers=headers)).json()
    assert session["status"] == "ready", session
    for item, right in zip(session["items"], results, strict=True):
        await client.post(
            f"{API}/practice/sessions/{session['id']}/answers",
            json={
                "question_id": item["question"]["id"],
                "option": 0 if right else 1,
                "time_taken_ms": 60_000,
            },
            headers=headers,
        )


async def test_the_dashboard_shows_the_week_strengths_weaknesses_tests_and_plan(
    client: AsyncClient, db_session: AsyncSession
):
    parent, child, chapter = await family_with_book(client)
    chapters = (await client.get(f"{API}/books/{chapter['book_id']}/chapters", headers=parent.headers)).json()
    first = (await client.get(f"{API}/chapters/{chapters[0]['id']}", headers=parent.headers)).json()
    await bank(db_session, parent, child, chapter, count=6)
    await bank(db_session, parent, child, first, count=5)
    topic = chapter["topics"][-1]
    await _practise(
        client,
        parent.headers,
        {"student_id": child["id"], "topic_id": topic["id"], "count": 5},
        [True, False, False, False, False],
    )
    await _practise(
        client, parent.headers, {"student_id": child["id"], "chapter_id": first["id"], "count": 5}, [True] * 5
    )
    test = (
        await client.post(
            f"{API}/mock-tests",
            json={"student_id": child["id"], "chapter_id": chapter["id"], "count": 1},
            headers=parent.headers,
        )
    ).json()
    sitting = (await client.post(f"{API}/mock-tests/{test['id']}/attempts", headers=parent.headers)).json()
    question = test["sections"][0]["questions"][0]["id"]
    await client.put(
        f"{API}/test-attempts/{sitting['id']}/answers/{question}", json={"option": 0}, headers=parent.headers
    )
    await client.post(f"{API}/test-attempts/{sitting['id']}/submit", headers=parent.headers)
    exam = recommendations.today() + timedelta(days=3)
    await client.post(
        f"{API}/study-plans", json={"student_id": child["id"], "exam_date": str(exam)}, headers=parent.headers
    )

    response = await client.get(f"{API}/students/{child['id']}/dashboard", headers=parent.headers)

    assert response.status_code == 200, response.text
    board = response.json()
    today = board["week"][-1]
    assert len(board["week"]) == 7 and today["day"] == str(recommendations.today())
    assert (today["answered"], today["correct"], today["minutes"]) == (11, 7, 10)  # the test answer counts
    assert {day["answered"] for day in board["week"][:-1]} == {0}
    assert [(area["chapter"], area["topic"]) for area in board["strong"]] == [
        ("Chapter 1 Rational Numbers", "1.2 Properties of Rational Numbers")
    ]
    assert [area["topic"] for area in board["needs_attention"]] == ["2.2 Solving Equations"]
    assert board["recommendations"][0]["kind"] == "strengthen"
    (result,) = board["tests"]
    assert (
        result["kind"],
        result["place"],
        result["score"],
        result["total_marks"],
        result["percentage"],
    ) == (
        "practice",
        "Chapter 2 Linear Equations in One Variable",
        1,
        1,
        100,
    )
    plan = board["plan"]
    assert (plan["exam_date"], plan["days_left"], plan["done"]) == (str(exam), 3, 0)
    assert plan["today"] and {item["day"] for item in plan["today"]} == {str(recommendations.today())}


async def test_a_new_learner_has_an_empty_dashboard_and_only_the_family_sees_it(client: AsyncClient):
    parent, child, _ = await family_with_book(client)
    sibling = await add_child(client, parent, class_level="class_7")
    stranger = await register(client)
    child_mode = await start_child_session(client, parent, child["id"])

    board = (await client.get(f"{API}/students/{child['id']}/dashboard", headers=child_mode)).json()

    assert [day["answered"] for day in board["week"]] == [0] * 7
    assert (board["strong"], board["needs_attention"], board["tests"], board["plan"]) == ([], [], [], None)
    assert [item["kind"] for item in board["recommendations"]] == ["new_chapter", "new_chapter"]
    for headers, student in ((child_mode, sibling), (stranger.headers, child)):
        refused = await client.get(f"{API}/students/{student['id']}/dashboard", headers=headers)
        assert (refused.status_code, error_code(refused)) == (404, "student_not_found")
