"""Mock tests: the paper, taking it against the clock, marking (with part marks) and the report.

Papers come from questions put straight into the family's question bank, so most tests need no AI;
written answers are marked by a scripted one.
"""

import uuid
from datetime import timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app import llm
from app.models import MockTestAttempt
from app.models.base import utcnow
from app.question_generation.schemas import Grade
from tests.api.helpers import (
    API,
    add_child,
    bank,
    error_code,
    family_with_book,
    register,
    start_child_session,
)
from tests.fakes import FakeLLM, QuestionWriterFake, make_question


@pytest.fixture
def ai(monkeypatch: pytest.MonkeyPatch):
    def install(fake):
        monkeypatch.setattr(llm, "get_llm_provider", lambda: fake)
        return fake

    return install


async def _chapter_test(client: AsyncClient, parent, child, chapter, **settings) -> dict:
    body = {"student_id": child["id"], "kind": "chapter", "chapter_id": chapter["id"], "count": 6, **settings}
    response = await client.post(f"{API}/mock-tests", json=body, headers=parent.headers)
    assert response.status_code == 201, response.text
    return response.json()


async def _fill_bank(db: AsyncSession, parent, child, chapter, mcq: int = 3, **formats: int) -> None:
    await bank(db, parent, child, chapter, count=mcq)
    for fmt, count in formats.items():
        await bank(db, parent, child, chapter, count=count, fmt=fmt)


def _ids(section: dict) -> list[str]:
    return [question["id"] for question in section["questions"]]


async def test_a_chapter_test_is_a_paper_in_sections_from_unseen_questions(
    client: AsyncClient, db_session: AsyncSession
):
    parent, child, chapter = await family_with_book(client)
    await _fill_bank(db_session, parent, child, chapter, mcq=5, short_answer=2, long_answer=1)
    practice = await client.post(
        f"{API}/practice/sessions",
        json={"student_id": child["id"], "chapter_id": chapter["id"], "count": 2, "question_type": "mcq"},
        headers=parent.headers,
    )
    seen = {item["question"]["id"] for item in practice.json()["items"]}

    test = await _chapter_test(client, parent, child, chapter)

    assert (test["status"], test["kind"], test["chapter"]) == (
        "ready",
        "chapter",
        "Chapter 2 Linear Equations in One Variable",
    )
    # Untimed: Class 7 has no timed tests.
    assert (test["total_marks"], test["duration_minutes"], test["attempts"]) == (12, None, [])
    assert [(s["code"], s["title"], s["marks"], len(s["questions"])) for s in test["sections"]] == [
        ("A", "Objective questions", 1, 3),
        ("C", "Short answer questions", 2, 2),
        ("D", "Long answer questions", 5, 1),
    ]
    numbers = [q["number"] for s in test["sections"] for q in s["questions"]]
    assert numbers == [1, 2, 3, 4, 5, 6]
    assert not seen & set(_ids(test["sections"][0]))  # never a question met in practice
    assert "answer" not in test["sections"][0]["questions"][0]
    assert (await client.get(f"{API}/mock-tests/{test['id']}", headers=parent.headers)).json() == test
    listed = (await client.get(f"{API}/students/{child['id']}/mock-tests", headers=parent.headers)).json()
    assert [item["id"] for item in listed["items"]] == [test["id"]] and listed["next_cursor"] is None

    # Not enough unseen questions left, and the AI is off: said at once.
    short = await client.post(
        f"{API}/mock-tests",
        json={"student_id": child["id"], "kind": "chapter", "chapter_id": chapter["id"]},
        headers=parent.headers,
    )
    assert short.status_code == 503 and error_code(short) == "ai_not_configured"


async def test_taking_a_test_then_marking_with_part_marks_and_the_report(
    client: AsyncClient, db_session: AsyncSession, ai
):
    parent, child, chapter = await family_with_book(client)
    await _fill_bank(db_session, parent, child, chapter, short_answer=2, long_answer=1)
    test = await _chapter_test(client, parent, child, chapter)
    (mcq1, mcq2, mcq3), (short1, _), (long1,) = (_ids(section) for section in test["sections"])

    started = await client.post(f"{API}/mock-tests/{test['id']}/attempts", headers=parent.headers)
    assert started.status_code == 201
    attempt = started.json()
    assert (attempt["status"], attempt["deadline"], attempt["responses"]) == ("in_progress", None, {})
    again = await client.post(f"{API}/mock-tests/{test['id']}/attempts", headers=parent.headers)
    assert again.json()["id"] == attempt["id"]  # the sitting in progress, not a second one
    base = f"{API}/test-attempts/{attempt['id']}"
    early = await client.get(f"{base}/report", headers=parent.headers)
    assert early.status_code == 422 and error_code(early) == "test_not_submitted"

    async def save(question_id: str, **answer) -> int:
        response = await client.put(f"{base}/answers/{question_id}", json=answer, headers=parent.headers)
        return response.status_code

    assert await save(mcq1, option=0, time_taken_ms=9000) == 204
    assert await save(mcq2, option=1) == 204
    assert await save(mcq2, option=0) == 204  # changed before submitting
    assert await save(mcq3, text="three") == 422  # does not fit a choice question
    assert await save(short1, text="Both sides stay the same.") == 204
    assert await save(long1, text="A partly right answer.") == 204
    assert await save(str(uuid.uuid4()), option=0) == 404
    saved = (await client.get(base, headers=parent.headers)).json()["responses"]
    assert len(saved) == 4 and saved[mcq2]["option"] == 0 and saved[mcq1]["time_taken_ms"] == 9000

    ai(
        FakeLLM(
            Grade(is_correct=True, key_points_covered=2, feedback="Well explained."),
            Grade(is_correct=False, key_points_covered=2, feedback="Add the other two points."),
        )
    )
    submitted = await client.post(f"{base}/submit", headers=parent.headers)

    assert submitted.status_code == 200, submitted.text
    report = submitted.json()
    assert (report["score"], report["total_marks"], report["percentage"]) == (6.5, 12, 54.2)
    assert (report["answered"], report["correct"], report["wrong"], report["unanswered"]) == (4, 3, 1, 2)
    assert [
        (s["code"], s["score"], s["total_marks"], s["answered"], s["correct"]) for s in report["sections"]
    ] == [
        ("A", 2, 3, 2, 2),
        ("C", 2, 4, 1, 1),
        ("D", 2.5, 5, 1, 0),  # 2 of the 4 key points: half the marks
    ]
    (area,) = report["areas"]
    assert (area["topic"], area["questions"], area["correct"], area["accuracy"]) == (
        "2.2 Solving Equations",
        6,
        3,
        0.5,
    )
    by_id = {q["question"]["id"]: q for q in report["questions"]}
    assert (by_id[mcq3]["marks_awarded"], by_id[mcq3]["correct"], by_id[mcq3]["response"]) == (
        None,
        None,
        None,
    )
    assert (by_id[long1]["marks_awarded"], by_id[long1]["feedback"]) == (2.5, "Add the other two points.")
    assert by_id[mcq1]["solution"]["final_answer"] == "right"

    assert await save(mcq3, option=0) == 422
    assert (await client.post(f"{base}/submit", headers=parent.headers)).json() == report  # once only
    assert (await client.get(f"{base}/report", headers=parent.headers)).json() == report

    # Test answers count like practice: mastery and progress.
    mastery = (await client.get(f"{API}/students/{child['id']}/mastery", headers=parent.headers)).json()
    assert [(a["attempts"], a["accuracy"]) for a in mastery["areas"]] == [(4, 0.75)]
    progress = (await client.get(f"{API}/students/{child['id']}/progress", headers=parent.headers)).json()
    assert (progress["questions_answered"], progress["correct_first_time"]) == (4, 3)

    retake = (await client.post(f"{API}/mock-tests/{test['id']}/attempts", headers=parent.headers)).json()
    assert retake["id"] != attempt["id"] and retake["responses"] == {}
    listed = (await client.get(f"{API}/students/{child['id']}/mock-tests", headers=parent.headers)).json()
    assert [(a["id"], a["score"]) for a in listed["items"][0]["attempts"]] == [
        (attempt["id"], 6.5),
        (retake["id"], None),
    ]


async def test_a_full_mock_test_runs_against_the_clock(client: AsyncClient, db_session: AsyncSession):
    parent, child, chapter = await family_with_book(client, class_level="class_10")
    await _fill_bank(db_session, parent, child, chapter, mcq=2, numerical=2, short_answer=2, long_answer=2)
    full = await client.post(
        f"{API}/mock-tests",
        json={"student_id": child["id"], "kind": "full_mock", "count": 4},
        headers=parent.headers,
    )
    assert full.status_code == 201, full.text
    test = full.json()
    assert [s["code"] for s in test["sections"]] == ["A", "B", "C", "D"]
    assert (test["total_marks"], test["duration_minutes"]) == (10, 20)  # about 2 minutes a mark
    timed = await _chapter_test(client, parent, child, chapter, count=4, duration_minutes=45)
    assert timed["duration_minutes"] == 45

    attempt = (await client.post(f"{API}/mock-tests/{test['id']}/attempts", headers=parent.headers)).json()
    assert 1190 <= attempt["seconds_left"] <= 1200
    numerical = test["sections"][1]["questions"][0]["id"]
    base = f"{API}/test-attempts/{attempt['id']}"
    assert (
        await client.put(f"{base}/answers/{numerical}", json={"value": 1}, headers=parent.headers)
    ).status_code == 204

    # 25 minutes later: past the deadline and the minute of grace.
    await db_session.execute(
        update(MockTestAttempt)
        .values(started_at=utcnow() - timedelta(minutes=25))
        .where(MockTestAttempt.id == uuid.UUID(attempt["id"]))
    )
    await db_session.commit()
    late = await client.put(f"{base}/answers/{numerical}", json={"value": 2}, headers=parent.headers)
    assert late.status_code == 422 and error_code(late) == "test_time_over"
    assert (await client.get(base, headers=parent.headers)).json()["seconds_left"] == 0

    # Submitting late still marks what was saved.
    report = (await client.post(f"{base}/submit", headers=parent.headers)).json()
    assert (report["score"], report["answered"], report["unanswered"]) == (2, 1, 3)
    assert report["time_taken_ms"] >= 25 * 60 * 1000


async def test_the_ai_writes_what_the_bank_lacks_section_by_section(client: AsyncClient, ai, task_queue):
    parent, child, chapter = await family_with_book(client)
    written = [
        make_question(
            format=fmt,
            text=f"Explain how to solve 2x + 4 = 10 ({fmt}).",
            options=[],
            correct_option=None,
            model_answer="Take 4 away from both sides, then divide by 2.",
            key_points=["take 4 away", "divide by 2"],
        )
        for fmt in ("short_answer", "long_answer")
    ]
    fake = ai(QuestionWriterFake([make_question()], *[[question] for question in written]))

    test = await _chapter_test(client, parent, child, chapter, count=3)

    assert test["status"] == "ready" and "prepare_test" in task_queue.jobs
    assert [(s["code"], [q["format"] for q in s["questions"]]) for s in test["sections"]] == [
        ("A", ["mcq"]),
        ("C", ["short_answer"]),
        ("D", ["long_answer"]),
    ]
    writes = [r for r in fake.requests if r["schema"].__name__ == "GeneratedBatch"]
    assert ["Formats to use: long_answer." in r["messages"][0].content for r in writes] == [
        False,
        False,
        True,
    ]


async def test_which_tests_each_class_may_take(client: AsyncClient):
    parent, child, chapter = await family_with_book(client)
    ukg = await add_child(client, parent, class_level="ukg")
    class_4 = await add_child(client, parent, class_level="class_4")

    async def refused(body: dict) -> tuple[str, str]:
        response = await client.post(f"{API}/mock-tests", json=body, headers=parent.headers)
        assert response.status_code == 422, response.text
        error = response.json()["error"]
        return error["code"], (error["details"] or [{}])[0].get("field", "")

    assert await refused({"student_id": ukg["id"]}) == ("test_not_for_class", "kind")
    assert await refused({"student_id": class_4["id"], "kind": "chapter", "chapter_id": chapter["id"]}) == (
        "test_not_for_class",
        "kind",
    )
    assert await refused({"student_id": child["id"], "kind": "full_mock"}) == ("test_not_for_class", "kind")
    assert await refused({"student_id": child["id"], "duration_minutes": 30}) == (
        "test_not_for_class",
        "duration_minutes",
    )
    assert (await refused({"student_id": child["id"], "kind": "chapter"}))[0] == "validation_error"
    assert (await refused({"student_id": child["id"], "kind": "full_mock", "chapter_id": chapter["id"]}))[
        0
    ] == "validation_error"
    assert await refused({"student_id": child["id"], "count": 31}) == ("validation_error", "count")


async def test_only_those_who_may_see_the_learner_see_their_tests(
    client: AsyncClient, db_session: AsyncSession
):
    parent, child, chapter = await family_with_book(client)
    await _fill_bank(db_session, parent, child, chapter, mcq=6, short_answer=4, long_answer=2)
    first = await _chapter_test(client, parent, child, chapter)
    second = await _chapter_test(client, parent, child, chapter)
    attempt = (await client.post(f"{API}/mock-tests/{first['id']}/attempts", headers=parent.headers)).json()
    question = first["sections"][0]["questions"][0]["id"]
    sibling = await add_child(client, parent, class_level="class_7")
    child_mode = await start_child_session(client, parent, child["id"])
    stranger = await register(client)
    theirs = await add_child(client, stranger, class_level="class_7")

    page = (await client.get(f"{API}/students/{child['id']}/mock-tests?limit=1", headers=child_mode)).json()
    assert [item["id"] for item in page["items"]] == [second["id"]]  # newest first
    rest = await client.get(
        f"{API}/students/{child['id']}/mock-tests?limit=1&cursor={page['next_cursor']}", headers=child_mode
    )
    assert [item["id"] for item in rest.json()["items"]] == [first["id"]]
    damaged = await client.get(
        f"{API}/students/{child['id']}/mock-tests?cursor=nonsense", headers=parent.headers
    )
    assert error_code(damaged) == "invalid_cursor"
    assert (
        await client.get(f"{API}/students/{sibling['id']}/mock-tests", headers=child_mode)
    ).status_code == 404

    base = f"{API}/test-attempts/{attempt['id']}"
    for method, path, code in [
        ("GET", f"{API}/mock-tests/{first['id']}", "test_not_found"),
        ("POST", f"{API}/mock-tests/{first['id']}/attempts", "test_not_found"),
        ("GET", base, "test_attempt_not_found"),
        ("PUT", f"{base}/answers/{question}", "test_attempt_not_found"),
        ("POST", f"{base}/submit", "test_attempt_not_found"),
        ("GET", f"{base}/report", "test_attempt_not_found"),
        ("GET", f"{API}/students/{child['id']}/mock-tests", "student_not_found"),
    ]:
        response = await client.request(method, path, json={"option": 0}, headers=stranger.headers)
        assert (response.status_code, error_code(response)) == (404, code), path
    borrowed = await client.post(
        f"{API}/mock-tests",
        json={"student_id": theirs["id"], "kind": "chapter", "chapter_id": chapter["id"]},
        headers=stranger.headers,
    )
    assert error_code(borrowed) == "chapter_not_found"
