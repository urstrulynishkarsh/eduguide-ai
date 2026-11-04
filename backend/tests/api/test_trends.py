"""Progress over time: weeks, subjects, kinds of question, difficulty, and test scores."""

import uuid
from datetime import timedelta

from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.adaptive_learning import recommendations
from app.models import QuestionAttempt
from app.models.base import utcnow
from tests.api.helpers import API, bank, error_code, family_with_book, register
from tests.api.test_adaptive import _practise
from tests.api.test_mock_tests import _chapter_test, _fill_bank, _ids


async def test_the_weeks_and_where_answers_go_right_or_wrong(client: AsyncClient, db_session: AsyncSession):
    parent, child, chapter = await family_with_book(client)
    await bank(db_session, parent, child, chapter, count=4)
    await _fill_bank(db_session, parent, child, chapter, mcq=3, short_answer=2, long_answer=1)
    body = {"student_id": child["id"], "chapter_id": chapter["id"], "count": 4, "question_type": "mcq"}
    first = await _practise(client, parent.headers, body, [True, True, True, False])
    # The first practice was three weeks ago.
    await db_session.execute(
        update(QuestionAttempt)
        .values(created_at=utcnow() - timedelta(weeks=3))
        .where(QuestionAttempt.practice_session_id == uuid.UUID(first["id"]))
    )
    await db_session.commit()
    test = await _chapter_test(client, parent, child, chapter)
    attempt = (await client.post(f"{API}/mock-tests/{test['id']}/attempts", headers=parent.headers)).json()
    base = f"{API}/test-attempts/{attempt['id']}"
    for question in _ids(test["sections"][0]):
        await client.put(f"{base}/answers/{question}", json={"option": 0}, headers=parent.headers)
    await client.post(f"{base}/submit", headers=parent.headers)

    response = await client.get(f"{API}/students/{child['id']}/progress/trends", headers=parent.headers)
    assert response.status_code == 200, response.text
    trends = response.json()

    today = recommendations.today()
    assert [week["day"] for week in trends["weeks"]][-1] == str(today - timedelta(days=today.weekday()))
    assert len(trends["weeks"]) == 12
    # Three weeks ago the practice, this week the test (its three objective questions, all right).
    assert [(w["answered"], w["correct"]) for w in trends["weeks"]][-4:] == [(4, 3), (0, 0), (0, 0), (3, 3)]
    everything = {"answered": 7, "accuracy": 0.857}
    assert trends["subjects"] == [{"code": "Mathematics", **everything}]
    assert (trends["formats"], trends["difficulties"]) == (
        [{"code": "mcq", **everything}],
        [{"code": "medium", **everything}],
    )
    assert [(t["kind"], t["score"], t["total_marks"]) for t in trends["tests"]] == [("chapter", 3, 12)]


async def test_only_the_family_sees_the_trends(client: AsyncClient):
    _, child, _ = await family_with_book(client)
    stranger = await register(client)
    refused = await client.get(f"{API}/students/{child['id']}/progress/trends", headers=stranger.headers)
    assert refused.status_code == 404 and error_code(refused) == "student_not_found"
