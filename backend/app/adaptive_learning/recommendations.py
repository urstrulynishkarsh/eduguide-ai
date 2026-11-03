"""Recommended for You (spec §11-12): at most three things to do next, kept for the day.

The list is made on the first request of the day (India time) from the learner's areas (mastery.py)
and books, in this order:

1. strengthen  - a weak area (below 60% right over at least 5 answers): a concept revision, then
                 practice at its level, which the adaptive rule has already lowered. Where the class
                 has no levels this is the gentle repetition of docs/07: the same, with easy questions.
2. continue    - an area being learned and practised in the last week, at its level
3. review      - an area not practised for a week or more
4. new_chapter - a chapter of the learner's books that has never been practised

Each one carries what Create Practice needs. Finishing a practice of its place marks it done.
"""

from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import ColumnElement, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.adaptive_learning import mastery
from app.class_profiles import get_class_profile
from app.models import Book, Chapter, PracticeSession, Recommendation, Student, StudentMastery
from app.models.base import utcnow
from app.schemas.adaptive import RecommendationOut, RecommendationsOut
from app.schemas.learn import ExplainRequest
from app.schemas.practice import PracticeCreate

INDIA = timezone(timedelta(hours=5, minutes=30))  # no daylight saving, so a fixed offset is exact
PER_DAY = 3
REVIEW_AFTER = timedelta(days=7)


def today() -> date:
    return datetime.now(INDIA).date()


def _right_lately(area: StudentMastery) -> str:
    return f"{round(area.accuracy * 100)}% right in the last {min(area.attempts, mastery.WINDOW)} answers"


async def _plan(
    db: AsyncSession, student: Student, learner_books: ColumnElement[bool]
) -> list[dict[str, Any]]:
    assert student.profile is not None
    features = get_class_profile(student.profile.class_level).features
    adaptive = features.adaptive_difficulty
    areas = (
        await db.scalars(
            select(StudentMastery)
            .where(StudentMastery.student_id == student.id)
            .order_by(StudentMastery.mastery, StudentMastery.last_practised_at)
        )
    ).all()
    week_ago = utcnow() - REVIEW_AFTER

    def level(area: StudentMastery, without_levels: str) -> str:
        return (area.difficulty or mastery.START_LEVEL) if adaptive else without_levels

    def item(kind: str, area: StudentMastery, difficulty: str, reason: str) -> dict[str, Any]:
        return {
            "kind": kind,
            "chapter_id": area.chapter_id,
            "topic_id": area.topic_id,
            "difficulty": difficulty,
            "reason": reason,
        }

    plan = []
    for area in filter(mastery.is_weak, areas):
        difficulty = level(area, "easy")
        if features.weak_topic_detection:
            reason = f"{_right_lately(area)}. Revise the idea, then practise {difficulty} questions."
        else:
            reason = "Let's practise this again, with easy questions."
        plan.append(item("strengthen", area, difficulty, reason))
    for area in areas:
        # Strong (at the hardest level, where there are levels): nothing to do until it is due a review.
        learnt = mastery.is_strong(area) and (not adaptive or area.difficulty == "hard")
        if not mastery.is_weak(area) and not learnt and area.last_practised_at >= week_ago:
            difficulty = level(area, "mixed")
            ahead = (
                f"Next: {difficulty} questions." if adaptive else "A little more practice makes it strong."
            )
            plan.append(item("continue", area, difficulty, f"{_right_lately(area)}. {ahead}"))
    for area in sorted(areas, key=lambda a: a.last_practised_at):
        if not mastery.is_weak(area) and area.last_practised_at < week_ago:
            days = (utcnow() - area.last_practised_at).days
            reason = f"Last practised {days} days ago. A short practice keeps it fresh."
            plan.append(item("review", area, level(area, "mixed"), reason))
    if len(plan) < PER_DAY:
        practised = select(StudentMastery.chapter_id).where(StudentMastery.student_id == student.id)
        chapters = await db.scalars(
            select(Chapter.id)
            .join(Book, Book.id == Chapter.book_id)
            .where(
                learner_books,
                Book.class_level == student.profile.class_level,
                Chapter.id.not_in(practised),
            )
            .order_by(Book.created_at, Chapter.number.asc().nulls_last(), Chapter.position)
            .limit(PER_DAY - len(plan))
        )
        plan += [
            {
                "kind": "new_chapter",
                "chapter_id": chapter_id,
                "topic_id": None,
                "difficulty": "mixed",
                "reason": "Not practised yet. Start with a short practice.",
            }
            for chapter_id in chapters
        ]
    return plan[:PER_DAY]


async def for_today(
    db: AsyncSession, student: Student, learner_books: ColumnElement[bool]
) -> RecommendationsOut:
    """Today's list, made now if this is the first request of the day. `learner_books` is the SQL
    condition on Book for the books this learner may practise from."""
    day = today()
    mine_today = (Recommendation.student_id == student.id, Recommendation.day == day)
    if await db.scalar(select(Recommendation.id).where(*mine_today).limit(1)) is None:
        plan = await _plan(db, student, learner_books)
        if plan:
            # Two first requests at once make the same list; the second one's rows are skipped.
            await db.execute(
                insert(Recommendation).on_conflict_do_nothing(),
                [
                    {
                        **planned,
                        "student_id": student.id,
                        "day": day,
                        "position": position,
                        "status": "active",
                    }
                    for position, planned in enumerate(plan)
                ],
            )
            await db.commit()
    rows = await db.execute(
        mastery.with_names(Recommendation).where(*mine_today).order_by(Recommendation.position)
    )
    items = []
    for row in rows:
        recommendation: Recommendation = row[0]
        place = mastery.names(row)
        practice = PracticeCreate(
            student_id=student.id,
            topic_id=recommendation.topic_id,
            chapter_id=None if recommendation.topic_id else recommendation.chapter_id,
            difficulty=recommendation.difficulty,
        )
        revise = None
        if recommendation.kind == "strengthen":
            revise = ExplainRequest(
                question=place["topic"] or place["chapter"],
                student_id=student.id,
                chapter_id=recommendation.chapter_id,
            )
        items.append(
            RecommendationOut(
                **place,
                id=recommendation.id,
                kind=recommendation.kind,
                status=recommendation.status,
                reason=recommendation.reason,
                practice=practice,
                revise=revise,
            )
        )
    return RecommendationsOut(student_id=student.id, day=day, items=items)


async def mark_done(db: AsyncSession, session: PracticeSession) -> None:
    """A finished practice: today's recommendation for its place is done (not committed)."""
    if session.chapter_id is None:
        return
    await db.execute(
        update(Recommendation)
        .where(
            Recommendation.student_id == session.student_id,
            Recommendation.day == today(),
            Recommendation.chapter_id == session.chapter_id,
            Recommendation.topic_id.is_not_distinct_from(session.topic_id),
        )
        .values(status="done")
    )
