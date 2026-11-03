"""Mastery after every answer, difficulty that follows it, and Recommended for You.

Practice here comes from questions put straight into the family's question bank, so no AI is needed;
answering goes through the API, as a learner would.
"""

from datetime import timedelta
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.adaptive_learning import recommendations
from app.models import StudentMastery
from app.models.base import utcnow
from tests.api.helpers import (
    API,
    Account,
    add_child,
    bank,
    error_code,
    family_with_book,
    register,
    start_child_session,
)


async def _practise(client: AsyncClient, headers: dict, body: dict[str, Any], results: list[bool]) -> dict:
    """A practice from the bank, answered right or wrong in this order."""
    session = (await client.post(f"{API}/practice/sessions", json=body, headers=headers)).json()
    assert session["status"] == "ready", session
    for item, right in zip(session["items"], results, strict=True):
        answered = await client.post(
            f"{API}/practice/sessions/{session['id']}/answers",
            json={"question_id": item["question"]["id"], "option": 0 if right else 1},
            headers=headers,
        )
        assert answered.status_code == 200, answered.text
    return session


async def _topic_practice(client, parent, child, chapter, results: list[bool]) -> dict:
    body = {"student_id": child["id"], "topic_id": chapter["topics"][-1]["id"], "count": len(results)}
    return await _practise(client, parent.headers, body, results)


async def _area(client: AsyncClient, parent: Account, child: dict) -> dict:
    areas = (await client.get(f"{API}/students/{child['id']}/mastery", headers=parent.headers)).json()[
        "areas"
    ]
    assert len(areas) == 1
    return areas[0]


async def _recommendations(client: AsyncClient, headers: dict, child: dict) -> list[dict]:
    response = await client.get(f"{API}/students/{child['id']}/recommendations", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()["items"]


async def test_the_level_rises_after_right_answers_and_falls_after_wrong_ones(
    client: AsyncClient, db_session: AsyncSession
):
    parent, child, chapter = await family_with_book(client)
    await bank(db_session, parent, child, chapter, count=20)

    await _topic_practice(client, parent, child, chapter, [True] * 4)
    area = await _area(client, parent, child)
    assert (area["topic"], area["chapter"]) == (
        "2.2 Solving Equations",
        "Chapter 2 Linear Equations in One Variable",
    )
    assert (area["attempts"], area["accuracy"], area["confidence"]) == (4, 1.0, 0.4)
    assert (area["difficulty"], area["status"]) == ("medium", "learning")  # 4 answers decide nothing yet

    await _topic_practice(client, parent, child, chapter, [True])
    area = await _area(client, parent, child)
    assert (area["difficulty"], area["status"], area["mastery"]) == ("hard", "strong", 1.0)

    await _topic_practice(client, parent, child, chapter, [False] * 4)
    assert (await _area(client, parent, child))["difficulty"] == "hard"  # 4 answers since it moved
    await _topic_practice(client, parent, child, chapter, [False])
    area = await _area(client, parent, child)
    assert (area["difficulty"], area["status"], area["accuracy"]) == ("medium", "needs_attention", 0.5)
    assert area["mastery"] < 0.5  # the recent wrong answers weigh more


async def test_a_weak_topic_gets_easier_practice_and_a_revision_until_it_is_done(
    client: AsyncClient, db_session: AsyncSession
):
    parent, child, chapter = await family_with_book(client)
    await bank(db_session, parent, child, chapter, count=5)
    await _topic_practice(client, parent, child, chapter, [True, False, False, False, False])

    first, new_chapter = await _recommendations(client, parent.headers, child)

    topic_id = chapter["topics"][-1]["id"]
    assert (first["kind"], first["status"], first["topic"]) == (
        "strengthen",
        "active",
        "2.2 Solving Equations",
    )
    assert (
        first["reason"] == "20% right in the last 5 answers. Revise the idea, then practise easy questions."
    )
    assert first["practice"] | {"student_id": None} == {
        "student_id": None,
        "book_id": None,
        "chapter_id": None,
        "topic_id": topic_id,
        "exercise_id": None,
        "count": None,
        "difficulty": "easy",
        "question_type": "mixed",
        "language": None,
    }
    assert first["revise"]["question"] == "2.2 Solving Equations"
    assert first["revise"]["chapter_id"] == chapter["id"]
    assert (new_chapter["kind"], new_chapter["chapter"]) == ("new_chapter", "Chapter 1 Rational Numbers")
    assert new_chapter["practice"]["chapter_id"] == new_chapter["chapter_id"]

    # Start Recommended Practice, as the screen will: the body as it came, 10 easy questions (Class 7).
    await bank(db_session, parent, child, chapter, count=10, difficulty="easy")
    await _practise(client, parent.headers, first["practice"], [True] * 10)

    again = await _recommendations(client, parent.headers, child)
    assert [item["id"] for item in again] == [first["id"], new_chapter["id"]]  # the same list all day
    assert [item["status"] for item in again] == ["done", "active"]


async def test_the_youngest_get_gentle_repetition_without_levels_or_labels(
    client: AsyncClient, db_session: AsyncSession
):
    parent, child, chapter = await family_with_book(client, class_level="ukg")
    await bank(db_session, parent, child, chapter, count=5)
    session = await _topic_practice(client, parent, child, chapter, [True, False, False, False, False])
    # Trying again until right is encouraged; only the first answer counts.
    retry = await client.post(
        f"{API}/practice/sessions/{session['id']}/answers",
        json={"question_id": session["items"][1]["question"]["id"], "option": 0},
        headers=parent.headers,
    )
    assert retry.json()["correct"] is True

    area = await _area(client, parent, child)
    assert (area["attempts"], area["accuracy"]) == (5, 0.2)
    assert (area["difficulty"], area["status"]) == (None, "learning")

    (first,) = await _recommendations(client, parent.headers, child)
    assert (first["kind"], first["practice"]["difficulty"]) == ("strengthen", "easy")
    assert first["reason"] == "Let's practise this again, with easy questions."


async def test_an_area_being_learned_continues_and_one_left_for_a_week_is_reviewed(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    parent, child, chapter = await family_with_book(client)
    await bank(db_session, parent, child, chapter, count=3)
    await _topic_practice(client, parent, child, chapter, [True, True, False])

    continuing, new_chapter = await _recommendations(client, parent.headers, child)
    assert (continuing["kind"], continuing["practice"]["difficulty"]) == ("continue", "medium")
    assert continuing["reason"] == "67% right in the last 3 answers. Next: medium questions."
    assert continuing["revise"] is None and new_chapter["kind"] == "new_chapter"

    # A new list the next day, when the topic was last practised eight days ago.
    await db_session.execute(update(StudentMastery).values(last_practised_at=utcnow() - timedelta(days=8)))
    await db_session.commit()
    tomorrow = recommendations.today() + timedelta(days=1)
    monkeypatch.setattr(recommendations, "today", lambda: tomorrow)

    review, _ = await _recommendations(client, parent.headers, child)
    assert (review["kind"], review["practice"]["difficulty"]) == ("review", "medium")
    assert review["reason"] == "Last practised 8 days ago. A short practice keeps it fresh."


async def test_a_new_learner_is_offered_the_chapters_of_their_own_books(client: AsyncClient):
    parent, child, _ = await family_with_book(client)
    sibling = await add_child(client, parent, class_level="class_7")

    items = await _recommendations(client, parent.headers, child)

    assert [(item["kind"], item["chapter"], item["topic"]) for item in items] == [
        ("new_chapter", "Chapter 1 Rational Numbers", None),
        ("new_chapter", "Chapter 2 Linear Equations in One Variable", None),
    ]
    mastery = await client.get(f"{API}/students/{child['id']}/mastery", headers=parent.headers)
    assert mastery.json()["areas"] == []
    assert await _recommendations(client, parent.headers, sibling) == []  # the book is not theirs


async def test_only_those_who_may_see_the_learner_get_their_mastery(client: AsyncClient):
    parent, child, _ = await family_with_book(client)
    sibling = await add_child(client, parent, class_level="class_7")
    stranger = await register(client)
    child_mode = await start_child_session(client, parent, child["id"])

    for path in ("mastery", "recommendations"):
        own = await client.get(f"{API}/students/{child['id']}/{path}", headers=child_mode)
        siblings = await client.get(f"{API}/students/{sibling['id']}/{path}", headers=child_mode)
        strangers = await client.get(f"{API}/students/{child['id']}/{path}", headers=stranger.headers)
        assert (own.status_code, siblings.status_code, strangers.status_code) == (200, 404, 404)
        assert error_code(strangers) == "student_not_found"
