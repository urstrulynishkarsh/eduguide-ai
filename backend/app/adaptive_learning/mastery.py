"""How well a learner knows each area, and the difficulty that follows it (spec §23, docs/07 §7.9).

An *area* is a topic of a chapter, or the chapter itself for questions that have no topic. After every
answer the numbers of the question's area are worked out again from the learner's history: the first
answer to each question in each practice (as basic progress counts them), the last 10 of them.

* accuracy   - the share that were right; the number the adaptive rule reads
* mastery    - the average `credit`, where recent answers and harder questions count more
* confidence - how much evidence there is: 10 answers = 1

Where the class has adaptive difficulty (Class 6-12) each area also has a level for its next practice.
It starts at medium and moves only on at least 5 answers given since it last moved: above 85% right
one level up, 60-85% it stays, below 60% one level down. Younger classes have no levels; their
recommendations repeat what needs practice, gently (recommendations.py).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import Row, Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.progress import first_answers
from app.class_profiles import ClassFeatures, get_class_profile
from app.models import Book, Chapter, Question, Recommendation, Student, StudentMastery, Topic
from app.rag.ingestion.labels import chapter_label, topic_label
from app.schemas.adaptive import AreaMastery, MasteryOut, MasteryStatus

WINDOW = 10  # the answers the numbers are worked out from
MIN_ANSWERS = 5  # before a level moves, or an area is called weak or strong
LEVEL_UP = 0.85  # share right above which the level goes up
WEAK = 0.60  # share right below which the level goes down and the area needs attention
STRONG = 0.85  # mastery from which an area is strong
LEVELS = ("easy", "medium", "hard")
START_LEVEL = "medium"
_RECENCY = 0.85  # each answer counts this much of the one after it
_DIFFICULTY_WEIGHT = {"easy": 1.0, "medium": 1.5, "hard": 2.0}
_HINT_COST = 0.25
_AFTER_SOLUTION = 0.25  # credit for a right answer given after the steps or the answer were shown


@dataclass(frozen=True, slots=True)
class Answer:
    correct: bool
    hints_used: int
    solution_viewed: bool
    difficulty: str
    at: datetime


def credit(answer: Answer) -> float:
    """1 for a right answer without help, a quarter less for each hint, a quarter after the solution."""
    if not answer.correct:
        return 0.0
    if answer.solution_viewed:
        return _AFTER_SOLUTION
    return max(_AFTER_SOLUTION, 1 - _HINT_COST * answer.hints_used)


def mastery(answers: Sequence[Answer]) -> float:
    """The weighted average credit of the answers, newest first."""
    weights = [_RECENCY**age * _DIFFICULTY_WEIGHT.get(a.difficulty, 1.0) for age, a in enumerate(answers)]
    return sum(w * credit(a) for w, a in zip(weights, answers, strict=True)) / sum(weights)


def accuracy(answers: Sequence[Answer]) -> float:
    return sum(a.correct for a in answers) / len(answers)


def next_level(level: str, since_last_move: Sequence[Answer]) -> str:
    """The adaptive rule, on the answers given since the level last moved (at most the last 10)."""
    if len(since_last_move) < MIN_ANSWERS:
        return level
    share = accuracy(since_last_move)
    step = 1 if share > LEVEL_UP else -1 if share < WEAK else 0
    return LEVELS[min(max(LEVELS.index(level) + step, 0), len(LEVELS) - 1)]


def is_weak(area: StudentMastery) -> bool:
    return area.attempts >= MIN_ANSWERS and area.accuracy < WEAK


def is_strong(area: StudentMastery) -> bool:
    return area.attempts >= MIN_ANSWERS and area.mastery >= STRONG


def status(area: StudentMastery, features: ClassFeatures) -> MasteryStatus:
    if features.weak_topic_detection and is_weak(area):
        return "needs_attention"
    return "strong" if is_strong(area) else "learning"


def practice_level(area: StudentMastery, features: ClassFeatures, without_levels: str) -> str:
    """The difficulty to practise an area at: its level where the class has levels."""
    return (area.difficulty or START_LEVEL) if features.adaptive_difficulty else without_levels


def right_lately(area: StudentMastery) -> str:
    """e.g. "33% right in the last 6 answers"."""
    return f"{round(area.accuracy * 100)}% right in the last {min(area.attempts, WINDOW)} answers"


async def record_answer(db: AsyncSession, student: Student, question: Question) -> None:
    """Works out the numbers of the question's area again, after an answer to it (not committed)."""
    if question.chapter_id is None:
        return
    first = first_answers(student.id)
    rows = (
        await db.execute(
            select(
                first.c.is_correct,
                first.c.hints_used,
                first.c.solution_viewed,
                first.c.difficulty,
                first.c.created_at,
                first.c.time_taken_ms,
                func.count().over().label("total"),
            )
            .join(Question, Question.id == first.c.question_id)
            .where(
                Question.chapter_id == question.chapter_id,
                Question.topic_id.is_not_distinct_from(question.topic_id),
            )
            .order_by(first.c.created_at.desc())
            .limit(WINDOW)
        )
    ).all()
    answers = [Answer(*row[:5]) for row in rows]
    times = [row.time_taken_ms for row in rows if row.time_taken_ms is not None]

    area = await db.scalar(
        select(StudentMastery).where(
            StudentMastery.student_id == student.id,
            StudentMastery.chapter_id == question.chapter_id,
            StudentMastery.topic_id.is_not_distinct_from(question.topic_id),
        )
    )
    if area is None:
        area = StudentMastery(
            student_id=student.id, chapter_id=question.chapter_id, topic_id=question.topic_id
        )
        db.add(area)
    area.attempts = rows[0].total
    area.accuracy = round(accuracy(answers), 3)
    area.mastery = round(mastery(answers), 3)
    area.confidence = round(min(1, area.attempts / WINDOW), 3)
    area.avg_time_ms = round(sum(times) / len(times)) if times else None
    area.last_practised_at = answers[0].at

    assert student.profile is not None
    if get_class_profile(student.profile.class_level).features.adaptive_difficulty:
        level = area.difficulty or START_LEVEL
        since = area.difficulty_since
        area.difficulty = next_level(level, [a for a in answers if since is None or a.at > since])
        if area.difficulty != level:
            area.difficulty_since = answers[0].at


# ---------------------------------------------------------------------------- reading areas


def with_names(table: type[StudentMastery] | type[Recommendation]) -> Select[Any]:
    """Rows of an area table, each with the names of its book, chapter and topic (see `names`)."""
    return (
        select(table, Book.id, Book.title, Chapter.number, Chapter.title, Topic.number, Topic.title)
        .join(Chapter, Chapter.id == table.chapter_id)
        .join(Book, Book.id == Chapter.book_id)
        .outerjoin(Topic, Topic.id == table.topic_id)
    )


def names(row: Row[Any]) -> dict[str, Any]:
    """The `Area` fields of a `with_names` row (or of a row of the same shape, where the chapter can be
    missing)."""
    item, book_id, book_title, chapter_number, chapter_title, topic_number, topic_title = row
    return {
        "book_id": book_id,
        "book_title": book_title,
        "chapter_id": item.chapter_id,
        "chapter": chapter_label(chapter_number, chapter_title) if chapter_title is not None else None,
        "topic_id": item.topic_id,
        "topic": topic_label(topic_number, topic_title) if topic_title is not None else None,
    }


async def knowledge_profile(db: AsyncSession, student: Student) -> MasteryOut:
    assert student.profile is not None
    features = get_class_profile(student.profile.class_level).features
    rows = await db.execute(
        with_names(StudentMastery)
        .where(StudentMastery.student_id == student.id)
        .order_by(StudentMastery.mastery, StudentMastery.last_practised_at.desc())
    )
    areas = []
    for row in rows:
        area: StudentMastery = row[0]
        areas.append(
            AreaMastery(
                **names(row),
                status=status(area, features),
                mastery=area.mastery,
                confidence=area.confidence,
                accuracy=area.accuracy,
                attempts=area.attempts,
                avg_time_ms=area.avg_time_ms,
                difficulty=area.difficulty if features.adaptive_difficulty else None,
                last_practised_at=area.last_practised_at,
            )
        )
    return MasteryOut(student_id=student.id, areas=areas)
