"""Misconceptions: repeated wrong ideas found in wrong answers, put right by right ones, and used by
the question writer. Practice comes from the question bank; the AI's reading is scripted."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app import llm
from app.adaptive_learning.misconceptions import FoundMisconception, MistakeReading
from app.models import StudentMisconception
from app.models.base import utcnow
from tests.api.helpers import API, bank, family_with_book
from tests.api.test_adaptive import _topic_practice
from tests.fakes import FakeLLM, QuestionWriterFake, make_question

SIGN = "Moves a number across the = sign without changing its sign."


@pytest.fixture
def ai(monkeypatch: pytest.MonkeyPatch):
    def install(fake):
        monkeypatch.setattr(llm, "get_llm_provider", lambda: fake)
        return fake

    return install


def _found(pattern: str, answers: list[int], same_as: int = 0) -> FoundMisconception:
    return FoundMisconception(
        pattern=pattern,
        fix="When a number moves across =, its sign changes.",
        explain_question="Why does the sign change when a number moves across the equals sign?",
        answers=answers,
        same_as=same_as,
    )


async def _misconceptions(client: AsyncClient, parent, child) -> list[dict]:
    response = await client.get(f"{API}/students/{child['id']}/misconceptions", headers=parent.headers)
    assert response.status_code == 200, response.text
    return response.json()["items"]


async def test_repeated_wrong_answers_become_a_misconception_and_right_ones_resolve_it(
    client: AsyncClient, db_session: AsyncSession, ai, task_queue
):
    parent, child, chapter = await family_with_book(client)
    await bank(db_session, parent, child, chapter, count=8)
    # A wrong idea two answers share is kept; one seen in a single answer is not.
    fake = ai(FakeLLM(MistakeReading(misconceptions=[_found(SIGN, [1, 3]), _found("A slip.", [2])])))

    await _topic_practice(client, parent, child, chapter, [False, False, True, False, True])

    # Looked at once, after the third wrong answer.
    assert task_queue.jobs.count("examine") == 1
    answers = fake.requests[0]["messages"][0].content
    assert "A3 [mcq]" in answers and "The student chose: (1) wrong" in answers
    (found,) = await _misconceptions(client, parent, child)
    topic = chapter["topics"][-1]
    assert (found["status"], found["pattern"], found["answers"], found["topic"]) == (
        "active",
        SIGN,
        2,
        "2.2 Solving Equations",
    )
    assert found["practice"]["topic_id"] == topic["id"]
    assert found["revise"]["question"].startswith("Why does the sign change")
    dashboard = (await client.get(f"{API}/students/{child['id']}/dashboard", headers=parent.headers)).json()
    assert [m["pattern"] for m in dashboard["misconceptions"]] == [SIGN]

    # Three right answers in a row in that topic put it right.
    await _topic_practice(client, parent, child, chapter, [True, True, True])
    (resolved,) = await _misconceptions(client, parent, child)
    assert resolved["status"] == "resolved" and resolved["resolved_at"]
    dashboard = (await client.get(f"{API}/students/{child['id']}/dashboard", headers=parent.headers)).json()
    assert dashboard["misconceptions"] == []


async def test_without_a_question_to_ask_the_wrong_idea_itself_is_explained(
    client: AsyncClient, db_session: AsyncSession, ai
):
    parent, child, chapter = await family_with_book(client)
    await bank(db_session, parent, child, chapter, count=3)
    # "Explain this" needs a question of two letters or more; the AI left this one empty.
    found = _found(SIGN, [1, 2]).model_copy(update={"explain_question": " "})
    ai(FakeLLM(MistakeReading(misconceptions=[found])))

    await _topic_practice(client, parent, child, chapter, [False, False, False])

    (shown,) = await _misconceptions(client, parent, child)
    assert shown["revise"]["question"] == SIGN
    dashboard = await client.get(f"{API}/students/{child['id']}/dashboard", headers=parent.headers)
    assert dashboard.status_code == 200, dashboard.text


async def test_the_question_writer_checks_the_misconceptions_of_the_place(
    client: AsyncClient, db_session: AsyncSession, ai
):
    parent, child, chapter = await family_with_book(client)
    topic = chapter["topics"][-1]
    db_session.add(
        StudentMisconception(
            student_id=uuid.UUID(child["id"]),
            chapter_id=uuid.UUID(chapter["id"]),
            topic_id=uuid.UUID(topic["id"]),
            pattern=SIGN,
            fix="-",
            explain_question="-",
            evidence=[],
            status="active",
            last_seen_at=utcnow(),
        )
    )
    await db_session.commit()
    writer = ai(QuestionWriterFake([make_question()]))

    body = {"student_id": child["id"], "topic_id": topic["id"], "count": 1}
    session = (await client.post(f"{API}/practice/sessions", json=body, headers=parent.headers)).json()

    assert session["status"] == "ready", session
    task = writer.requests[0]["messages"][0].content
    assert f"This student keeps making these mistakes here: {SIGN}" in task


async def test_the_youngest_are_not_looked_at_and_others_cannot_see(
    client: AsyncClient, db_session, ai, task_queue
):
    parent, child, chapter = await family_with_book(client, "ukg")
    await bank(db_session, parent, child, chapter, count=3)
    ai(FakeLLM())
    await _topic_practice(client, parent, child, chapter, [False, False, False])
    assert "examine" not in task_queue.jobs
    assert await _misconceptions(client, parent, child) == []

    stranger, _, _ = await family_with_book(client)
    response = await client.get(f"{API}/students/{child['id']}/misconceptions", headers=stranger.headers)
    assert response.status_code == 404
