"""Basic performance of one learner (spec §32): how much, how well, where.

Accuracy uses the first answer to each question in a practice or a test, so trying again (encouraged
for the youngest children) does not inflate it. Mastery (adaptive_learning/mastery.py) uses the
same rule. Test answers count like practice answers; the sessions listed are practice sessions.
"""

import uuid
from collections.abc import Callable
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import ColumnElement, Date, Integer, Subquery, cast, func, select
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Chapter, PracticeItem, PracticeSession, Question, QuestionAttempt, Topic
from app.rag.ingestion.labels import chapter_label
from app.schemas.dashboard import DayProgress, Share
from app.schemas.practice import AreaProgress, ProgressOut, SessionSummary

_RECENT_SESSIONS = 5
INDIA = timezone(timedelta(hours=5, minutes=30))  # no daylight saving, so a fixed offset is exact


def first_answers(student_id: uuid.UUID) -> Subquery:
    """The learner's first answer to each question in each practice and each test sitting (every
    attempt column). One of the two ids is always empty, and DISTINCT ON treats empty ones as equal."""
    answered_in = (
        QuestionAttempt.practice_session_id,
        QuestionAttempt.test_attempt_id,
        QuestionAttempt.question_id,
    )
    return (
        select(QuestionAttempt)
        .where(QuestionAttempt.student_id == student_id)
        .ext(distinct_on(*answered_in))
        .order_by(*answered_in, QuestionAttempt.created_at)
        .subquery()
    )


async def progress(db: AsyncSession, student_id: uuid.UUID) -> ProgressOut:
    first = first_answers(student_id)
    correct = func.sum(cast(first.c.is_correct, Integer))
    answered, right, hints = (
        await db.execute(
            select(func.count(), func.coalesce(correct, 0), func.coalesce(func.sum(first.c.hints_used), 0))
        )
    ).one()
    time_spent = await db.scalar(
        select(func.coalesce(func.sum(QuestionAttempt.time_taken_ms), 0)).where(
            QuestionAttempt.student_id == student_id
        )
    )

    per_area = (
        select(func.count(), func.avg(cast(first.c.is_correct, Integer)))
        .select_from(first)
        .join(Question, Question.id == first.c.question_id)
        .order_by(func.count().desc())
    )
    chapter_rows = await db.execute(
        per_area.add_columns(Chapter.id, Chapter.number, Chapter.title)
        .join(Chapter, Chapter.id == Question.chapter_id)
        .group_by(Chapter.id)
    )
    topic_rows = await db.execute(
        per_area.add_columns(Topic.id, Topic.title)
        .join(Topic, Topic.id == Question.topic_id)
        .group_by(Topic.id)
    )
    chapters = [
        AreaProgress(id=id_, name=chapter_label(number, title), attempted=n, accuracy=round(float(avg), 3))
        for n, avg, id_, number, title in chapter_rows
    ]
    topics = [
        AreaProgress(id=id_, name=title, attempted=n, accuracy=round(float(avg), 3))
        for n, avg, id_, title in topic_rows
    ]

    items = select(func.count()).where(PracticeItem.session_id == PracticeSession.id).scalar_subquery()
    done = select(func.count()).where(first.c.practice_session_id == PracticeSession.id).scalar_subquery()
    good = (
        select(func.count())
        .where(first.c.practice_session_id == PracticeSession.id, first.c.is_correct)
        .scalar_subquery()
    )
    recent = await db.execute(
        select(PracticeSession, items, done, good)
        .where(PracticeSession.student_id == student_id)
        .order_by(PracticeSession.created_at.desc())
        .limit(_RECENT_SESSIONS)
    )
    completed = await db.scalar(
        select(func.count()).where(
            PracticeSession.student_id == student_id, PracticeSession.status == "completed"
        )
    )
    return ProgressOut(
        student_id=student_id,
        questions_answered=answered,
        correct_first_time=right,
        accuracy=round(right / answered, 3) if answered else None,
        time_spent_ms=time_spent or 0,
        hints_used=hints,
        sessions_completed=completed or 0,
        by_chapter=chapters,
        by_topic=topics,
        recent_sessions=[
            SessionSummary(
                id=session.id,
                status=session.status,
                questions=count,
                answered=answered_count,
                correct=correct_count,
                created_at=session.created_at,
            )
            for session, count, answered_count, correct_count in recent
        ],
    )


def _india_day(moment: ColumnElement) -> ColumnElement[date]:
    return cast(func.timezone("Asia/Kolkata", moment), Date)


def _india_week(moment: ColumnElement) -> ColumnElement[date]:
    """The Monday of the week (India time)."""
    return cast(func.date_trunc("week", func.timezone("Asia/Kolkata", moment)), Date)


async def _periods(
    db: AsyncSession,
    student_id: uuid.UUID,
    starts: list[date],
    period: Callable[[ColumnElement], ColumnElement[date]],
) -> list[DayProgress]:
    """For each period (a day or a week, by its first day, oldest first): first answers, how many were
    right, and the minutes spent answering (every attempt, as in `progress`)."""
    since = datetime.combine(starts[0], time(), INDIA)
    first = first_answers(student_id)
    key = period(first.c.created_at).label("key")
    answers = {
        row.key: row
        for row in await db.execute(
            select(
                key,
                func.count().label("answered"),
                func.sum(cast(first.c.is_correct, Integer)).label("right"),
            )
            .where(first.c.created_at >= since)
            .group_by(key)
        )
    }
    attempt_key = period(QuestionAttempt.created_at).label("key")
    time_spent = dict(
        (
            await db.execute(
                select(attempt_key, func.sum(QuestionAttempt.time_taken_ms))
                .where(QuestionAttempt.student_id == student_id, QuestionAttempt.created_at >= since)
                .group_by(attempt_key)
            )
        ).all()
    )
    return [
        DayProgress(
            day=start,
            answered=answers[start].answered if start in answers else 0,
            correct=answers[start].right if start in answers else 0,
            minutes=round((time_spent.get(start) or 0) / 60000),
        )
        for start in starts
    ]


async def week(db: AsyncSession, student_id: uuid.UUID, today: date) -> list[DayProgress]:
    """The 7 days up to `today` (India time), oldest first."""
    days = [today - timedelta(days=back) for back in range(6, -1, -1)]
    return await _periods(db, student_id, days, _india_day)


async def weeks(db: AsyncSession, student_id: uuid.UUID, today: date, count: int) -> list[DayProgress]:
    """The `count` weeks up to this one (Monday to Sunday, India time), oldest first; each by its Monday."""
    monday = today - timedelta(days=today.weekday())
    return await _periods(
        db, student_id, [monday - timedelta(weeks=back) for back in range(count - 1, -1, -1)], _india_week
    )


async def shares(db: AsyncSession, student_id: uuid.UUID) -> tuple[list[Share], list[Share], list[Share]]:
    """How well each subject, kind of question and difficulty goes (first answers), most answered first."""
    first = first_answers(student_id)

    async def by(column: ColumnElement[str]) -> list[Share]:
        rows = await db.execute(
            select(column, func.count(), func.avg(cast(first.c.is_correct, Integer)))
            .select_from(first)
            .join(Question, Question.id == first.c.question_id)
            .group_by(column)
            .order_by(func.count().desc(), column)
        )
        return [Share(code=code, answered=n, accuracy=round(float(avg), 3)) for code, n, avg in rows]

    return await by(Question.subject), await by(Question.format), await by(first.c.difficulty)
