"""Create Practice -> answer -> help -> progress, with a scripted AI."""

import uuid
from contextlib import asynccontextmanager

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import llm
from app.models import PracticeSession, Question, QuestionAttempt
from app.question_generation.schemas import Grade
from app.rag.answering import Explanation
from app.services import practice_service
from tests.api.helpers import API, add_child, create_book, error_code, register, start_child_session, upload
from tests.fakes import QuestionWriterFake, make_question
from tests.samples import NOTES_TEXT, make_pdf


@pytest.fixture
def writer(monkeypatch: pytest.MonkeyPatch):
    def install(*batches, reject=(), extra=()) -> QuestionWriterFake:
        fake = QuestionWriterFake(*batches, reject=reject, extra=extra)
        monkeypatch.setattr(llm, "get_llm_provider", lambda: fake)
        return fake

    return install


def _three() -> list:
    return [
        make_question(text="What is x if x - 2 = 7?", options=["5", "7", "9", "11"], correct_option=2),
        make_question(text="What is y if y + 3 = 10?", options=["6", "7", "8", "13"], correct_option=1),
        make_question(
            format="short_answer",
            style="conceptual",
            text="Why do we do the same thing to both sides of an equation?",
            options=[],
            correct_option=None,
            model_answer="To keep both sides equal.",
            key_points=["both sides stay equal"],
        ),
    ]


async def _family(client: AsyncClient, class_level: str = "class_8"):
    parent = await register(client)
    child = await add_child(client, parent, class_level=class_level)
    book = await create_book(client, parent.headers, student_id=child["id"], class_level=None)
    await upload(client, parent.headers, book["id"], make_pdf())
    chapters = (await client.get(f"{API}/books/{book['id']}/chapters", headers=parent.headers)).json()
    chapter = (await client.get(f"{API}/chapters/{chapters[1]['id']}", headers=parent.headers)).json()
    return parent, child, chapter


async def _create(client: AsyncClient, parent, child, chapter, **settings):
    payload = {
        "student_id": child["id"],
        "exercise_id": chapter["exercises"][0]["id"],
        "count": 3,
        **settings,
    }
    return await client.post(f"{API}/practice/sessions", json=payload, headers=parent.headers)


async def test_create_practice_from_an_exercise(client: AsyncClient, writer):
    parent, child, chapter = await _family(client)
    fake = writer(_three())

    response = await _create(client, parent, child, chapter)

    assert response.status_code == 201, response.text
    session = response.json()
    assert session["status"] == "ready"  # the test queue prepares it at once
    assert session["question_count"] == 3 and len(session["items"]) == 3
    first = session["items"][0]["question"]
    assert first["origin"] == "generated"
    assert first["options"] == ["5", "7", "9", "11"]
    assert first["source"]["chapter"] == "Chapter 2 Linear Equations in One Variable"
    assert "answer" not in first and "correct_option" not in str(first)
    assert session["items"][0]["hints_total"] == 2
    # The writer got the exercise's own questions as material, and the class profile.
    task = fake.requests[0]["messages"][0].content
    assert "Solve the following equations." in task
    assert "Class 8" in fake.requests[0]["system"]


async def test_create_practice_for_one_topic(client: AsyncClient, writer, db_session: AsyncSession):
    parent, child, chapter = await _family(client)
    topic = chapter["topics"][-1]
    fake = writer(_three()[:1])
    body = {"student_id": child["id"], "topic_id": topic["id"], "count": 1}

    response = await client.post(f"{API}/practice/sessions", json=body, headers=parent.headers)

    assert response.status_code == 201 and response.json()["status"] == "ready"
    assert "we do the same operation on both sides" in fake.requests[0]["messages"][0].content
    # Filed under the topic, so the next practice of this topic finds it in the question bank.
    question_id = uuid.UUID(response.json()["items"][0]["question"]["id"])
    assert str((await db_session.get(Question, question_id)).topic_id) == topic["id"]

    stranger = await register(client)
    their_child = await add_child(client, stranger, class_level="class_8")
    borrowed = await client.post(
        f"{API}/practice/sessions", json={**body, "student_id": their_child["id"]}, headers=stranger.headers
    )
    assert borrowed.status_code == 404 and error_code(borrowed) == "topic_not_found"
    two_places = await client.post(
        f"{API}/practice/sessions", json={**body, "chapter_id": chapter["id"]}, headers=parent.headers
    )
    assert two_places.status_code == 422


async def test_answers_help_and_completion(client: AsyncClient, writer, db_session: AsyncSession):
    parent, child, chapter = await _family(client)
    writer(_three(), extra=[Grade(is_correct=True, feedback="Yes - both sides stay equal.")])
    session = (await _create(client, parent, child, chapter)).json()
    q1, q2, q3 = (item["question"]["id"] for item in session["items"])
    base = f"{API}/practice/sessions/{session['id']}"

    hint = (
        await client.post(f"{base}/questions/{q2}/help", json={"level": "hint"}, headers=parent.headers)
    ).json()
    assert (hint["hint"], hint["hints_left"], hint["final_answer"]) == (
        "Take 4 away from both sides.",
        1,
        None,
    )
    second = (
        await client.post(f"{base}/questions/{q2}/help", json={"level": "hint"}, headers=parent.headers)
    ).json()
    assert second["hint"] == "Then divide both sides by 2." and second["hints_left"] == 0
    steps = (
        await client.post(f"{base}/questions/{q2}/help", json={"level": "steps"}, headers=parent.headers)
    ).json()
    assert steps["steps"] == ["2x = 6", "x = 3"] and steps["final_answer"] is None

    right = (
        await client.post(f"{base}/answers", json={"question_id": q1, "option": 2}, headers=parent.headers)
    ).json()
    assert right == {
        "correct": True,
        "try_again": False,
        "feedback": None,
        "correct_answer": "x = 3",
        "session_completed": False,
    }
    wrong = await client.post(
        f"{base}/answers",
        json={"question_id": q2, "option": 0, "time_taken_ms": 12000},
        headers=parent.headers,
    )
    assert wrong.json()["correct"] is False and wrong.json()["correct_answer"] == "x = 3"
    written = await client.post(
        f"{base}/answers",
        json={"question_id": q3, "text": "so both sides stay the same"},
        headers=parent.headers,
    )
    assert written.json()["feedback"] == "Yes - both sides stay equal."
    assert written.json()["session_completed"] is True

    attempt = await db_session.scalar(select(QuestionAttempt).where(QuestionAttempt.question_id == q2))
    assert (attempt.hints_used, attempt.solution_viewed, attempt.time_taken_ms) == (2, True, 12000)

    shape = await client.post(
        f"{base}/answers", json={"question_id": q1, "text": "nine"}, headers=parent.headers
    )
    assert shape.status_code == 422 and error_code(shape) == "answer_does_not_fit"

    done = (await client.get(base, headers=parent.headers)).json()
    assert (done["status"], done["answered"], done["correct"]) == ("completed", 3, 2)


async def test_progress_counts_first_answers_by_chapter(client: AsyncClient, writer):
    parent, child, chapter = await _family(client)
    writer(_three())
    session = (await _create(client, parent, child, chapter)).json()
    q1, q2, _ = (item["question"]["id"] for item in session["items"])
    base = f"{API}/practice/sessions/{session['id']}"
    await client.post(
        f"{base}/answers",
        json={"question_id": q1, "option": 2, "time_taken_ms": 5000},
        headers=parent.headers,
    )
    await client.post(
        f"{base}/answers",
        json={"question_id": q2, "option": 0, "time_taken_ms": 7000},
        headers=parent.headers,
    )
    await client.post(
        f"{base}/answers", json={"question_id": q2, "option": 1}, headers=parent.headers
    )  # retry

    progress = (await client.get(f"{API}/students/{child['id']}/progress", headers=parent.headers)).json()

    assert (progress["questions_answered"], progress["correct_first_time"], progress["accuracy"]) == (
        2,
        1,
        0.5,
    )
    assert progress["time_spent_ms"] == 12000
    assert progress["by_chapter"] == [
        {
            "id": chapter["id"],
            "name": "Chapter 2 Linear Equations in One Variable",
            "attempted": 2,
            "accuracy": 0.5,
        }
    ]
    assert progress["recent_sessions"][0]["answered"] == 2


async def test_saved_questions_are_reused_without_the_ai(client: AsyncClient, writer, monkeypatch):
    parent, child, chapter = await _family(client)
    writer(_three())
    await _create(client, parent, child, chapter)
    sibling = await add_child(client, parent, class_level="class_8")

    monkeypatch.setattr(llm, "get_llm_provider", lambda: (_ for _ in ()).throw(llm.AINotConfiguredError()))
    reused = await _create(client, parent, sibling, chapter)

    assert reused.status_code == 201
    assert reused.json()["status"] == "ready" and len(reused.json()["items"]) == 3
    # The first child has seen them; with the AI off there is nothing new to write.
    again = await _create(client, parent, child, chapter)
    assert again.status_code == 503 and error_code(again) == "ai_not_configured"


async def test_the_youngest_are_invited_to_try_again(client: AsyncClient, writer):
    parent = await register(client)
    child = await add_child(client, parent, class_level="ukg")
    book = await create_book(
        client,
        parent.headers,
        title="My first book",
        subject="English",
        student_id=child["id"],
        class_level=None,
    )
    await upload(client, parent.headers, book["id"], NOTES_TEXT.encode(), "water.txt", "text/plain")
    picture = make_question(
        format="visual_choice",
        text="Which one is water?",
        options=["💧 Water", "🍎 Apple", "🚗 Car"],
        correct_option=0,
        hints=["You can drink it."],
        steps=["Water is what we drink."],
        final_answer="💧 Water",
    )
    writer([picture])
    session = (
        await client.post(
            f"{API}/practice/sessions", json={"student_id": child["id"], "count": 1}, headers=parent.headers
        )
    ).json()
    session_mode = await start_child_session(client, parent, child["id"])
    question_id = session["items"][0]["question"]["id"]

    wrong = await client.post(
        f"{API}/practice/sessions/{session['id']}/answers",
        json={"question_id": question_id, "option": 1},
        headers=session_mode,
    )

    assert wrong.json()["try_again"] is True
    assert wrong.json()["correct_answer"] is None


async def test_settings_must_fit_the_class(client: AsyncClient, writer):
    parent, child, chapter = await _family(client)
    writer()
    too_many = await _create(client, parent, child, chapter, count=31)
    assert too_many.status_code == 422
    not_for_class = await _create(client, parent, child, chapter, question_type="numerical")
    assert error_code(not_for_class) == "question_type_not_for_class"
    two_places = await _create(client, parent, child, chapter, book_id=chapter["book_id"])
    assert two_places.status_code == 422


async def test_failed_generation_is_reported_in_parent_words(client: AsyncClient, writer):
    parent, child, chapter = await _family(client)
    broken = [make_question(text=f"Broken {n}", options=["1"]) for n in range(3)]
    writer([broken[0]], [broken[1]], [broken[2]])

    session = (await _create(client, parent, child, chapter, count=1)).json()

    assert session["status"] == "failed"
    assert session["error"] == {
        "code": "generation_failed",
        "message": "We couldn't create practice questions this time. Please try again.",
    }


async def test_practice_left_preparing_by_a_restart_is_finished(
    client: AsyncClient, writer, db_session: AsyncSession, task_queue
):
    parent, child, chapter = await _family(client)
    writer(_three())
    stuck = PracticeSession(
        student_id=uuid.UUID(child["id"]),
        book_id=uuid.UUID(chapter["book_id"]),
        chapter_id=uuid.UUID(chapter["id"]),
        exercise_id=uuid.UUID(chapter["exercises"][0]["id"]),
        question_count=3,
        difficulty="mixed",
        question_type="mixed",
        language="en",
        status="preparing",
    )
    db_session.add(stuck)
    await db_session.commit()

    @asynccontextmanager
    async def test_session():
        yield db_session

    await practice_service.resume_unfinished_sessions(test_session, task_queue)

    session = (await client.get(f"{API}/practice/sessions/{stuck.id}", headers=parent.headers)).json()
    assert session["status"] == "ready" and len(session["items"]) == 3


async def test_explain_a_question_in_hindi(client: AsyncClient, writer):
    parent, child, chapter = await _family(client)
    explanation = Explanation(
        enough_information=True, explanation="दोनों ओर से 2 जोड़ें।", steps=[], sources_used=["S1"]
    )
    fake = writer(_three(), extra=[explanation])
    session = (await _create(client, parent, child, chapter)).json()
    question_id = session["items"][0]["question"]["id"]

    response = await client.post(
        f"{API}/practice/sessions/{session['id']}/questions/{question_id}/explain",
        json={"style": "hindi"},
        headers=parent.headers,
    )

    assert response.status_code == 200
    assert response.json()["explanation"] == "दोनों ओर से 2 जोड़ें।"
    assert response.json()["sources"]
    prompt = fake.requests[-1]["messages"][0].content
    assert "Write in Hindi" in prompt and "Stay consistent with this worked solution" in prompt


async def test_other_families_cannot_see_or_answer(client: AsyncClient, writer):
    parent, child, chapter = await _family(client)
    writer(_three())
    session = (await _create(client, parent, child, chapter)).json()
    stranger = await register(client)
    question_id = session["items"][0]["question"]["id"]
    base = f"{API}/practice/sessions/{session['id']}"

    responses = [
        await client.get(base, headers=stranger.headers),
        await client.post(
            f"{base}/answers", json={"question_id": question_id, "option": 2}, headers=stranger.headers
        ),
        await client.post(
            f"{base}/questions/{question_id}/help", json={"level": "answer"}, headers=stranger.headers
        ),
        await client.get(f"{API}/students/{child['id']}/progress", headers=stranger.headers),
    ]
    assert [r.status_code for r in responses] == [404] * 4
    their_child = await add_child(client, stranger, class_level="class_8")
    borrowed = await _create(client, stranger, their_child, chapter)
    assert borrowed.status_code == 404
