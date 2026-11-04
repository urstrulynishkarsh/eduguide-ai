"""The question bank, shared by practice sessions and mock tests.

Both ask for questions through `QuestionSettings` (a place, a difficulty, a language). Checked
questions from the family's bank that the learner has never been given - in any practice or test -
come first; only the shortfall is written and checked by the AI, in a background job
(`preparing` -> `ready`, or `failed` with a reason). New questions are saved to the bank, filed
under the place they were written for, so the next practice or test there finds them.
"""

import logging
import random
import uuid
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass

from sqlalchemy import ColumnElement, and_, exists, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app import llm
from app.adaptive_learning import misconceptions
from app.auth.principal import Principal
from app.class_profiles import ClassProfile
from app.core.enums import QuestionFormat
from app.core.errors import InvalidInputError
from app.models import (
    Book,
    DocumentChunk,
    MockTest,
    MockTestQuestion,
    PracticeItem,
    PracticeSession,
    Question,
    Student,
)
from app.models.practice import QuestionSettings
from app.question_generation import generator
from app.question_generation.schemas import CHOICE_FORMATS, NUMBER_FORMATS, GeneratedQuestion
from app.rag import retrieval
from app.schemas.practice import QuestionRequest
from app.services import library_service, student_service

logger = logging.getLogger(__name__)

_ERROR_MESSAGES = {
    "insufficient_context": retrieval.InsufficientContextError.message,
    "ai_unavailable": llm.AIUnavailableError.message,
    "generation_failed": "We couldn't create practice questions this time. Please try again.",
}


def error_message(code: str) -> str:
    return _ERROR_MESSAGES.get(code, _ERROR_MESSAGES["generation_failed"])


def check_count(profile: ClassProfile, count: int) -> None:
    if count > profile.max_session_questions:
        raise InvalidInputError(
            f"{profile.label} has at most {profile.max_session_questions} questions at a time.",
            details=[{"field": "count", "message": f"At most {profile.max_session_questions}."}],
        )


async def set_place(
    db: AsyncSession, principal: Principal, row: QuestionSettings, data: QuestionRequest
) -> None:
    """Copies the chosen place onto `row`, with the wider places it is in. It must be one this session
    may see (404 otherwise)."""
    if data.exercise_id:
        exercise, chapter, book = await library_service.get_exercise(db, principal, data.exercise_id)
        row.exercise_id, row.chapter_id, row.book_id = exercise.id, chapter.id, book.id
    elif data.topic_id:
        topic, chapter = await library_service.get_topic(db, principal, data.topic_id)
        row.topic_id, row.chapter_id, row.book_id = topic.id, chapter.id, chapter.book_id
    elif data.chapter_id:
        chapter = await library_service.get_chapter(db, principal, data.chapter_id)
        row.chapter_id, row.book_id = chapter.id, chapter.book_id
    elif data.book_id:
        row.book_id = (await library_service.get_book(db, principal, data.book_id)).id


@dataclass(frozen=True, slots=True)
class ChapterPlace:
    """One chapter of a wider request, asked for like it (a previous-year pattern test spreads its
    sections over the chapters that carry the most marks)."""

    chapter_id: uuid.UUID
    difficulty: str
    language: str
    book_id: None = None
    topic_id: None = None
    exercise_id: None = None


# Where questions come from, at what difficulty and in what language.
Place = QuestionSettings | ChapterPlace


def _learner_books(owner: uuid.UUID, student: Student) -> ColumnElement[bool]:
    return library_service.books_for_learner(owner, student.id)


def _place_filter(owner: uuid.UUID, row: Place, student: Student) -> ColumnElement[bool]:
    """SQL conditions on Question for the row's place."""
    if row.exercise_id:
        return Question.exercise_id == row.exercise_id
    if row.topic_id:
        return Question.topic_id == row.topic_id
    if row.chapter_id:
        return Question.chapter_id == row.chapter_id
    if row.book_id:
        return Question.book_id == row.book_id
    assert student.profile is not None
    learner_books = select(Book.id).where(_learner_books(owner, student))
    return and_(Question.book_id.in_(learner_books), Question.class_level == student.profile.class_level)


def _given_to(student: Student) -> ColumnElement[bool]:
    """SQL condition on Question: given to this learner before, in a practice or a test."""
    sessions = select(PracticeSession.id).where(PracticeSession.student_id == student.id)
    tests = select(MockTest.id).where(MockTest.student_id == student.id)
    return exists().where(
        PracticeItem.question_id == Question.id, PracticeItem.session_id.in_(sessions)
    ) | exists().where(MockTestQuestion.question_id == Question.id, MockTestQuestion.mock_test_id.in_(tests))


async def from_bank(
    db: AsyncSession,
    owner: uuid.UUID,
    row: Place,
    student: Student,
    formats: Sequence[str],
    limit: int,
) -> list[Question]:
    """Checked questions for the row's place that this learner has never been given."""
    query = select(Question).where(
        Question.owner_user_id == owner,
        _place_filter(owner, row, student),
        Question.language == row.language,
        Question.format.in_(formats),
        ~_given_to(student),
    )
    if row.difficulty != "mixed":
        query = query.where(Question.difficulty == row.difficulty)
    return list((await db.scalars(query.order_by(Question.created_at).limit(limit))).all())


async def _passages(
    db: AsyncSession, owner: uuid.UUID, row: Place, student: Student, budget: int
) -> list[retrieval.Passage]:
    """The book text for the row's place (at most `budget` tokens), exercise or topic first when one
    was chosen."""
    places: list[retrieval.ChunkFilter] = []
    if row.exercise_id:
        places.append(retrieval.ChunkFilter(owner, exercise_id=row.exercise_id))
    if row.topic_id:
        places.append(retrieval.ChunkFilter(owner, topic_id=row.topic_id))
    if row.chapter_id:
        places.append(retrieval.ChunkFilter(owner, chapter_id=row.chapter_id))
    elif row.book_id:
        places.append(retrieval.ChunkFilter(owner, book_ids=[row.book_id]))
    else:
        assert student.profile is not None
        books = (await db.scalars(select(Book.id).where(_learner_books(owner, student)))).all()
        places.append(retrieval.ChunkFilter(owner, book_ids=books, class_level=student.profile.class_level))
    found: list[retrieval.Passage] = []
    for where in places:
        found += await retrieval.passages_at(db, where, token_budget=budget)
    return retrieval.build_context(found, token_budget=budget)


def to_question(
    generated: GeneratedQuestion,
    owner: uuid.UUID,
    row: Place,
    student: Student,
    chunks: dict[str, DocumentChunk],
) -> Question:
    cited = [chunks[tag] for tag in generated.source_tags]
    first = cited[0]
    fmt = generated.format
    body: dict = {"text": generated.text}
    if generated.case:
        body["case"] = generated.case
    if generated.unit:
        body["unit"] = generated.unit
    if fmt in CHOICE_FORMATS:
        body["options"] = generated.options
        answer: dict = {"option": generated.correct_option}
    elif fmt in NUMBER_FORMATS:
        answer = {"value": generated.numeric_answer}
    elif fmt is QuestionFormat.FILL_BLANK:
        answer = {"accepted": [a for a in generated.accepted_answers if a.strip()]}
    elif fmt is QuestionFormat.MATCHING:
        order = list(range(len(generated.match_right)))
        random.shuffle(order)  # shown in a mixed-up order; pairs[i] is where left[i]'s match ended up
        body["left"] = generated.match_left
        body["right"] = [generated.match_right[i] for i in order]
        answer = {"pairs": [order.index(i) for i in range(len(order))]}
    else:
        answer = {"model_answer": generated.model_answer, "key_points": generated.key_points}
    assert student.profile is not None
    return Question(
        owner_user_id=owner,
        book_id=first.book_id,
        chapter_id=first.chapter_id,
        # Written for a topic or an exercise: filed under it, so the next request for it finds it.
        topic_id=row.topic_id or first.topic_id,
        exercise_id=row.exercise_id or first.exercise_id,
        origin="generated",
        class_level=student.profile.class_level,
        subject=first.subject,
        format=fmt.value,
        style=generated.style.value,
        difficulty=generated.difficulty,
        language=row.language,
        body=body,
        answer=answer,
        hints=generated.hints,
        solution={
            "concept": generated.concept,
            "steps": generated.steps,
            "final_answer": generated.final_answer,
        },
        source_chunk_ids=[str(chunk.id) for chunk in cited],
        page=first.page_start,
        validation={"checked_by": "independent review"},
    )


async def write(
    db: AsyncSession,
    owner: uuid.UUID,
    row: Place,
    student: Student,
    *,
    formats: list[QuestionFormat],
    count: int,
) -> list[Question]:
    """Up to `count` new questions for the row's place, written and checked by the AI and saved to the
    bank (flushed, not committed). Raises InsufficientContextError when the place has no text."""
    assert student.profile is not None
    budget = llm.get_llm_provider().request_size.passage_tokens
    passages = await _passages(db, owner, row, student, budget)
    if not passages:
        raise retrieval.InsufficientContextError()
    existing = (
        await db.scalars(
            select(Question.body["text"].astext).where(
                Question.owner_user_id == owner, _place_filter(owner, row, student)
            )
        )
    ).all()
    written = await generator.generate(
        passages,
        profile=student_service.class_profile(student),
        student=student.profile,
        request=generator.Request(
            count=count,
            difficulty=row.difficulty,
            formats=formats,
            language=row.language,
            mistakes=tuple(
                await misconceptions.for_place(
                    db, student.id, book_id=row.book_id, chapter_id=row.chapter_id, topic_id=row.topic_id
                )
            ),
        ),
        existing=list(existing),
    )
    chunks = {passage.tag: passage.chunk for passage in passages}
    questions = [to_question(q, owner, row, student, chunks) for q in written]
    db.add_all(questions)
    await db.flush()
    return questions


# ---------------------------------------------------------------------------- the background job


async def _fail(db: AsyncSession, model: type[QuestionSettings], row_id: uuid.UUID, code: str) -> None:
    await db.rollback()
    row = await db.get(model, row_id, populate_existing=True)
    if row is not None:
        row.status, row.error_code = "failed", code
        await db.commit()


Fill = Callable[[AsyncSession, QuestionSettings, Student, uuid.UUID], Awaitable[int]]


async def prepare(db: AsyncSession, model: type[QuestionSettings], row_id: uuid.UUID, fill: Fill) -> None:
    """The background job of a practice or test that is `preparing`: `fill(db, row, student, owner)`
    writes the questions it still needs and returns how many it has now. Then it is `ready` - or
    `failed`, with the reason, when it has none. Safe to run again."""
    row = await db.get(model, row_id)
    if row is None or row.status != "preparing":
        return
    student = await db.get(Student, row.student_id)
    assert student is not None
    owner = await student_service.account_of(db, student)
    try:
        if await fill(db, row, student, owner) == 0:
            await _fail(db, model, row_id, "generation_failed")
            return
        row.status = "ready"
        await db.commit()
        logger.info("%s %s ready", model.__name__, row_id)
    except retrieval.InsufficientContextError:
        await _fail(db, model, row_id, "insufficient_context")
    except (llm.AIUnavailableError, llm.AINotConfiguredError):
        await _fail(db, model, row_id, "ai_unavailable")
    except Exception:
        logger.exception("Preparing %s %s failed", model.__name__, row_id)
        await _fail(db, model, row_id, "generation_failed")


async def preparing(
    session_factory: async_sessionmaker[AsyncSession], model: type[QuestionSettings]
) -> Sequence[uuid.UUID]:
    """At start-up: the rows whose questions were being written when the server stopped."""
    async with session_factory() as db:
        ids = (await db.scalars(select(model.id).where(model.status == "preparing"))).all()
    if ids:
        logger.info("Resuming %d %s row(s) being prepared", len(ids), model.__name__)
    return ids
