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

import uuid
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import ColumnElement, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.adaptive_learning import mastery
from app.analytics.progress import INDIA
from app.class_profiles import get_class_profile
from app.models import Book, Chapter, PracticeSession, Recommendation, Student, StudentMastery
from app.models.base import utcnow
from app.schemas.adaptive import RecommendationOut, RecommendationsOut
from app.schemas.learn import ExplainRequest
from app.schemas.practice import PracticeCreate

PER_DAY = 3
REVIEW_AFTER = timedelta(days=7)


def today() -> date:
    return datetime.now(INDIA).date()


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

    def item(kind: str, area: StudentMastery, difficulty: str, reason: dict[str, Any]) -> dict[str, Any]:
        return {
            "kind": kind,
            "chapter_id": area.chapter_id,
            "topic_id": area.topic_id,
            "difficulty": difficulty,
            "reason": reason,
        }

    plan = []
    for area in filter(mastery.is_weak, areas):
        difficulty = mastery.practice_level(area, features, "easy")
        if features.weak_topic_detection:
            reason = {"code": "weak", **mastery.right_lately(area), "difficulty": difficulty}
        else:
            reason = {"code": "again"}
        plan.append(item("strengthen", area, difficulty, reason))
    for area in areas:
        # Strong (at the hardest level, where there are levels): nothing to do until it is due a review.
        learnt = mastery.is_strong(area) and (not adaptive or area.difficulty == "hard")
        if not mastery.is_weak(area) and not learnt and area.last_practised_at >= week_ago:
            difficulty = mastery.practice_level(area, features, "mixed")
            ahead = {"code": "next_level", "difficulty": difficulty} if adaptive else {"code": "keep_going"}
            plan.append(item("continue", area, difficulty, {**ahead, **mastery.right_lately(area)}))
    for area in sorted(areas, key=lambda a: a.last_practised_at):
        if not mastery.is_weak(area) and area.last_practised_at < week_ago:
            reason = {"code": "review", "days": (utcnow() - area.last_practised_at).days}
            plan.append(item("review", area, mastery.practice_level(area, features, "mixed"), reason))
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
                "reason": {"code": "new_chapter"},
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
        revise = revise_body(student.id, place) if recommendation.kind == "strengthen" else None
        items.append(
            RecommendationOut(
                **place,
                id=recommendation.id,
                kind=recommendation.kind,
                status=recommendation.status,
                reason=recommendation.reason,
                practice=practice_body(student.id, place, recommendation.difficulty),
                revise=revise,
            )
        )
    return RecommendationsOut(student_id=student.id, day=day, items=items)


def practice_body(student_id: uuid.UUID, place: dict[str, Any], difficulty: str) -> PracticeCreate:
    """Create Practice for an area (`mastery.names`): its topic, or the chapter in general."""
    return PracticeCreate(
        student_id=student_id,
        topic_id=place["topic_id"],
        chapter_id=None if place["topic_id"] else place["chapter_id"],
        difficulty=difficulty,
    )


def revise_body(student_id: uuid.UUID, place: dict[str, Any]) -> ExplainRequest:
    """The "Explain this" request for an area (`mastery.names`), searched in its chapter."""
    return ExplainRequest(
        question=place["topic"] or place["chapter"], student_id=student_id, chapter_id=place["chapter_id"]
    )


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
