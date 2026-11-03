"""Practice sessions: Create Practice, prepare the questions, answer, ask for help, explain.

Creating a session first reuses checked questions from the family's question bank that this
learner has not seen; only the shortfall is written by the AI, in the background (`preparing` ->
`ready`). Every answer is stored as an attempt, with the help the learner opened before answering.

Who sees what: a session belongs to one learner and is visible to whoever may see that learner.
"""

import logging
import random
import uuid

from sqlalchemy import ColumnElement, and_, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app import llm
from app.auth.principal import Principal
from app.class_profiles import ClassProfile, get_class_profile
from app.core.enums import ClassLevel, LearningBand, QuestionFormat
from app.core.errors import InvalidInputError, NotFoundError
from app.core.tasks import TaskQueue
from app.models import Book, DocumentChunk, PracticeItem, PracticeSession, Question, QuestionAttempt, Student
from app.models.base import utcnow
from app.question_generation import checking, generator, strategy
from app.question_generation.schemas import CHOICE_FORMATS, NUMBER_FORMATS, WRITTEN_FORMATS, GeneratedQuestion
from app.rag import answering, retrieval
from app.rag.answering import ExplainStyle
from app.schemas.learn import ExplainResponse
from app.schemas.practice import AnswerIn, AnswerResult, HelpLevel, HelpOut, PracticeCreate
from app.services import library_service, student_service

logger = logging.getLogger(__name__)

PASSAGE_BUDGET = 6000  # tokens of book text given to the question writer

SESSION_ERROR_MESSAGES = {
    "insufficient_context": retrieval.InsufficientContextError.message,
    "ai_unavailable": llm.AIUnavailableError.message,
    "generation_failed": "We couldn't create practice questions this time. Please try again.",
}


def _profile(student: Student) -> ClassProfile:
    assert student.profile is not None
    return get_class_profile(ClassLevel(student.profile.class_level))


def _place_filter(owner: uuid.UUID, session: PracticeSession, student: Student) -> ColumnElement[bool]:
    """SQL conditions on Question for the session's place (bank reuse)."""
    if session.exercise_id:
        return Question.exercise_id == session.exercise_id
    if session.chapter_id:
        return Question.chapter_id == session.chapter_id
    if session.book_id:
        return Question.book_id == session.book_id
    assert student.profile is not None
    learner_books = select(Book.id).where(library_service.books_for_learner(owner, student.id))
    return and_(Question.book_id.in_(learner_books), Question.class_level == student.profile.class_level)


async def _from_bank(
    db: AsyncSession,
    owner: uuid.UUID,
    session: PracticeSession,
    student: Student,
    formats: list[str],
    limit: int,
) -> list[Question]:
    """Checked questions for this place that this learner has never been given (in any session)."""
    learner_sessions = select(PracticeSession.id).where(PracticeSession.student_id == student.id)
    query = select(Question).where(
        Question.owner_user_id == owner,
        _place_filter(owner, session, student),
        Question.language == session.language,
        Question.format.in_(formats),
        ~exists().where(
            PracticeItem.question_id == Question.id, PracticeItem.session_id.in_(learner_sessions)
        ),
    )
    if session.difficulty != "mixed":
        query = query.where(Question.difficulty == session.difficulty)
    return list((await db.scalars(query.order_by(Question.created_at).limit(limit))).all())


def _add_items(db: AsyncSession, session: PracticeSession, questions: list[Question], start: int) -> None:
    db.add_all(
        PracticeItem(session_id=session.id, question_id=q.id, position=start + i)
        for i, q in enumerate(questions)
    )


async def create_session(
    db: AsyncSession, principal: Principal, data: PracticeCreate, *, queue: TaskQueue
) -> PracticeSession:
    student = await student_service.learner_for(db, principal, data.student_id)
    profile = _profile(student)
    assert student.profile is not None

    count = data.count or profile.default_session_questions
    if count > profile.max_session_questions:
        raise InvalidInputError(
            f"{profile.label} practice has at most {profile.max_session_questions} questions.",
            details=[{"field": "count", "message": f"At most {profile.max_session_questions}."}],
        )
    formats = strategy.allowed_formats(profile, data.question_type)
    if not formats:
        raise InvalidInputError(
            f"{data.question_type} questions are not used in {profile.label}.",
            code="question_type_not_for_class",
            details=[{"field": "question_type", "message": "Not used for this class."}],
        )

    session = PracticeSession(
        student_id=student.id,
        question_count=count,
        difficulty=data.difficulty,
        question_type=data.question_type,
        language=data.language or student.profile.primary_language,
        status="preparing",
    )
    # The chosen place must be one this session may see (404 otherwise).
    if data.exercise_id:
        exercise, chapter, book = await library_service.get_exercise(db, principal, data.exercise_id)
        session.exercise_id, session.chapter_id, session.book_id = exercise.id, chapter.id, book.id
    elif data.chapter_id:
        chapter = await library_service.get_chapter(db, principal, data.chapter_id)
        session.chapter_id, session.book_id = chapter.id, chapter.book_id
    elif data.book_id:
        session.book_id = (await library_service.get_book(db, principal, data.book_id)).id
    db.add(session)
    await db.flush()

    owner = await student_service.account_of(db, student)
    reused = await _from_bank(db, owner, session, student, formats, count)
    _add_items(db, session, reused, 0)
    if len(reused) < count:
        llm.get_llm_provider()  # 503 now, rather than a failed session later, when AI is switched off
    else:
        session.status = "ready"
    await db.commit()
    if session.status == "preparing":
        await queue.enqueue(prepare_session, session_id=session.id)
    return session


# ---------------------------------------------------------------------------- the background job


async def _passages(
    db: AsyncSession, owner: uuid.UUID, session: PracticeSession, student: Student
) -> list[retrieval.Passage]:
    """The book text for the session's place, exercise first when one was chosen."""
    budget = PASSAGE_BUDGET
    places: list[retrieval.ChunkFilter] = []
    if session.exercise_id:
        places.append(retrieval.ChunkFilter(owner, exercise_id=session.exercise_id))
    if session.chapter_id:
        places.append(retrieval.ChunkFilter(owner, chapter_id=session.chapter_id))
    elif session.book_id:
        places.append(retrieval.ChunkFilter(owner, book_ids=[session.book_id]))
    else:
        assert student.profile is not None
        books = (
            await db.scalars(select(Book.id).where(library_service.books_for_learner(owner, student.id)))
        ).all()
        places.append(retrieval.ChunkFilter(owner, book_ids=books, class_level=student.profile.class_level))
    found: list[retrieval.Passage] = []
    for where in places:
        found += await retrieval.passages_at(db, where, token_budget=budget)
    return retrieval.build_context(found, token_budget=budget)


def _to_question(
    generated: GeneratedQuestion,
    owner: uuid.UUID,
    session: PracticeSession,
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
        topic_id=first.topic_id,
        # Written for an exercise: filed under it, so the next session for that exercise finds it.
        exercise_id=session.exercise_id or first.exercise_id,
        origin="generated",
        class_level=student.profile.class_level,
        subject=first.subject,
        format=fmt.value,
        style=generated.style.value,
        difficulty=generated.difficulty,
        language=session.language,
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


async def _fail(db: AsyncSession, session_id: uuid.UUID, code: str) -> None:
    await db.rollback()
    session = await db.get(PracticeSession, session_id, populate_existing=True)
    if session is not None:
        session.status, session.error_code = "failed", code
        await db.commit()


async def prepare_session(db: AsyncSession, *, session_id: uuid.UUID) -> None:
    """The background job that writes the questions a session still needs. Safe to run again."""
    session = await db.get(PracticeSession, session_id)
    if session is None or session.status != "preparing":
        return
    student = await db.get(Student, session.student_id)
    assert student is not None and student.profile is not None
    profile = _profile(student)
    owner = await student_service.account_of(db, student)
    try:
        have = await db.scalar(select(func.count()).where(PracticeItem.session_id == session.id)) or 0
        passages = await _passages(db, owner, session, student)
        if not passages:
            await _fail(db, session_id, "insufficient_context")
            return
        existing = (
            await db.scalars(
                select(Question.body["text"].astext).where(
                    Question.owner_user_id == owner, _place_filter(owner, session, student)
                )
            )
        ).all()
        request = generator.Request(
            count=session.question_count - have,
            difficulty=session.difficulty,
            formats=strategy.allowed_formats(profile, session.question_type),
            language=session.language,
        )
        written = await generator.generate(
            passages, profile=profile, student=student.profile, request=request, existing=list(existing)
        )
        if not written and have == 0:
            await _fail(db, session_id, "generation_failed")
            return
        chunks = {passage.tag: passage.chunk for passage in passages}
        questions = [_to_question(q, owner, session, student, chunks) for q in written]
        db.add_all(questions)
        await db.flush()
        _add_items(db, session, questions, have)
        session.status = "ready"
        await db.commit()
        logger.info("Practice session %s ready: %d reused, %d written", session_id, have, len(questions))
    except (llm.AIUnavailableError, llm.AINotConfiguredError):
        await _fail(db, session_id, "ai_unavailable")
    except Exception:
        logger.exception("Preparing practice session %s failed", session_id)
        await _fail(db, session_id, "generation_failed")


async def resume_unfinished_sessions(
    session_factory: async_sessionmaker[AsyncSession], queue: TaskQueue
) -> None:
    """At start-up: sessions whose questions were being written when the server stopped are queued again."""
    async with session_factory() as db:
        ids = (
            await db.scalars(select(PracticeSession.id).where(PracticeSession.status == "preparing"))
        ).all()
    for session_id in ids:
        await queue.enqueue(prepare_session, session_id=session_id)
    if ids:
        logger.info("Resumed preparing %d practice session(s)", len(ids))


# ---------------------------------------------------------------------------- doing the practice


async def get_session(db: AsyncSession, principal: Principal, session_id: uuid.UUID) -> PracticeSession:
    session = await db.scalar(
        select(PracticeSession)
        .join(Student, Student.id == PracticeSession.student_id)
        .where(PracticeSession.id == session_id, student_service.visible_to(principal))
        .execution_options(populate_existing=True)
    )
    if session is None:
        raise NotFoundError("We couldn't find this practice.", code="practice_not_found")
    return session


async def session_items(
    db: AsyncSession, session: PracticeSession
) -> list[tuple[PracticeItem, Question, int, bool | None]]:
    """Each question with its help state, number of attempts and the latest result."""
    latest = (
        select(QuestionAttempt.is_correct)
        .where(QuestionAttempt.practice_session_id == session.id, QuestionAttempt.question_id == Question.id)
        .order_by(QuestionAttempt.created_at.desc())
        .limit(1)
        .scalar_subquery()
    )
    attempts = (
        select(func.count())
        .where(QuestionAttempt.practice_session_id == session.id, QuestionAttempt.question_id == Question.id)
        .scalar_subquery()
    )
    rows = await db.execute(
        select(PracticeItem, Question, attempts, latest)
        .join(Question, Question.id == PracticeItem.question_id)
        .where(PracticeItem.session_id == session.id)
        .order_by(PracticeItem.position)
    )
    return [(item, question, count, correct) for item, question, count, correct in rows]


async def _item(
    db: AsyncSession, session: PracticeSession, question_id: uuid.UUID
) -> tuple[PracticeItem, Question]:
    row = (
        await db.execute(
            select(PracticeItem, Question)
            .join(Question, Question.id == PracticeItem.question_id)
            .where(PracticeItem.session_id == session.id, PracticeItem.question_id == question_id)
        )
    ).first()
    if row is None:
        raise NotFoundError("This question is not part of this practice.", code="question_not_found")
    item, question = row
    return item, question


async def answer(
    db: AsyncSession, principal: Principal, session_id: uuid.UUID, data: AnswerIn
) -> AnswerResult:
    session = await get_session(db, principal, session_id)
    if session.status not in ("ready", "completed"):
        raise InvalidInputError("This practice is not ready yet.", code="practice_not_ready")
    item, question = await _item(db, session, data.question_id)
    student = await db.get(Student, session.student_id)
    assert student is not None and student.profile is not None
    profile = _profile(student)

    response = data.model_dump(include={"option", "value", "text", "pairs"}, exclude_none=True)
    feedback = None
    if question.format in WRITTEN_FORMATS:
        if not data.text:
            raise InvalidInputError("Please write an answer.", code="answer_does_not_fit")
        grade = await checking.mark_written(question, data.text, profile=profile, student=student.profile)
        correct, feedback = grade.is_correct, grade.feedback
    else:
        try:
            correct = checking.is_correct(question, response)
        except checking.AnswerShapeError as exc:
            raise InvalidInputError(str(exc), code="answer_does_not_fit") from None

    db.add(
        QuestionAttempt(
            student_id=student.id,
            question_id=question.id,
            practice_session_id=session.id,
            response=response,
            is_correct=correct,
            feedback=feedback,
            time_taken_ms=data.time_taken_ms,
            hints_used=item.hints_shown,
            solution_viewed=item.steps_shown or item.answer_shown,
            difficulty=question.difficulty,
        )
    )
    await db.flush()
    unanswered = await db.scalar(
        select(func.count())
        .select_from(PracticeItem)
        .where(
            PracticeItem.session_id == session.id,
            ~exists().where(
                QuestionAttempt.practice_session_id == session.id,
                QuestionAttempt.question_id == PracticeItem.question_id,
            ),
        )
    )
    if unanswered == 0 and session.status != "completed":
        session.status, session.completed_at = "completed", utcnow()
    await db.commit()

    # Nursery - Class 2: never "wrong" - an invitation to try again, answer kept back.
    try_again = not correct and profile.band is LearningBand.FOUNDATIONAL
    return AnswerResult(
        correct=correct,
        try_again=try_again,
        feedback=feedback,
        correct_answer=None if try_again else question.solution["final_answer"],
        session_completed=session.status == "completed",
    )


async def help_with(
    db: AsyncSession, principal: Principal, session_id: uuid.UUID, question_id: uuid.UUID, level: HelpLevel
) -> HelpOut:
    """Hint -> Show Steps -> Show Answer (spec §20). Hints come one at a time."""
    session = await get_session(db, principal, session_id)
    item, question = await _item(db, session, question_id)
    solution = question.solution
    hint = None
    if level == "hint":
        index = min(item.hints_shown, len(question.hints) - 1)
        hint = question.hints[index]
        item.hints_shown = min(item.hints_shown + 1, len(question.hints))
    elif level == "steps":
        item.steps_shown = True
    else:
        item.answer_shown = True
    await db.commit()
    return HelpOut(
        level=level,
        hint=hint,
        hints_left=len(question.hints) - item.hints_shown,
        concept=solution["concept"] if level != "hint" else None,
        steps=solution["steps"] if level != "hint" else [],
        final_answer=solution["final_answer"] if level == "answer" else None,
    )


async def explain_question(
    db: AsyncSession, principal: Principal, session_id: uuid.UUID, question_id: uuid.UUID, style: ExplainStyle
) -> ExplainResponse:
    """ "Explain simply / like I'm 10 / in Hindi / in Hinglish" for one question, from its own passages."""
    llm.get_llm_provider()
    session = await get_session(db, principal, session_id)
    _, question = await _item(db, session, question_id)
    student = await db.get(Student, session.student_id)
    assert student is not None and student.profile is not None
    chunk_ids = [uuid.UUID(chunk_id) for chunk_id in question.source_chunk_ids]
    chunks = (await db.scalars(select(DocumentChunk).where(DocumentChunk.id.in_(chunk_ids)))).all()
    passages = retrieval.build_context([retrieval.Passage(chunk, 1.0) for chunk in chunks])
    if not passages:
        raise retrieval.InsufficientContextError()
    solution = question.solution
    answer_ = await answering.explain(
        question.body["text"],
        passages=passages,
        profile=_profile(student),
        student=student.profile,
        style=style,
        worked_solution="\n".join([solution["concept"], *solution["steps"], solution["final_answer"]]),
    )
    if not answer_.enough_information:
        raise retrieval.InsufficientContextError()
    cited = [p.chunk for p in passages if p.tag in answer_.sources_used]
    return ExplainResponse(
        explanation=answer_.explanation,
        steps=answer_.steps,
        style=style,
        sources=await library_service.describe_sources(
            db, [(c.book_id, c.chapter_id, c.exercise_id, c.page_start) for c in cited]
        ),
    )


def session_error_message(code: str) -> str:
    return SESSION_ERROR_MESSAGES.get(code, SESSION_ERROR_MESSAGES["generation_failed"])
