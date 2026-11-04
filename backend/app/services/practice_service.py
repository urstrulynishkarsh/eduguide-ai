"""Practice sessions: Create Practice, prepare the questions, answer, ask for help, explain.

Creating a session first reuses checked questions from the family's question bank that this
learner has not seen; only the shortfall is written by the AI, in the background (`preparing` ->
`ready`; services/question_bank.py). Every answer is stored as an attempt, with the help the
learner opened before answering, and updates the learner's mastery of the question's topic
(adaptive_learning). A finished practice ticks off today's recommendation and study-plan task for
its place.

Who sees what: a session belongs to one learner and is visible to whoever may see that learner.
"""

import uuid

from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app import llm
from app.adaptive_learning import mastery, misconceptions, recommendations
from app.auth.principal import Principal
from app.core.enums import LearningBand
from app.core.errors import InvalidInputError, NotFoundError
from app.core.tasks import TaskQueue
from app.models import DocumentChunk, PracticeItem, PracticeSession, Question, QuestionAttempt, Student
from app.models.base import utcnow
from app.question_generation import checking, strategy
from app.rag import answering, retrieval
from app.rag.answering import ExplainStyle
from app.schemas.learn import ExplainResponse
from app.schemas.practice import AnswerIn, AnswerResult, HelpLevel, HelpOut, PracticeCreate
from app.services import library_service, question_bank, student_service, study_plan_service


def _add_items(db: AsyncSession, session: PracticeSession, questions: list[Question], start: int) -> None:
    db.add_all(
        PracticeItem(session_id=session.id, question_id=q.id, position=start + i)
        for i, q in enumerate(questions)
    )


async def create_session(
    db: AsyncSession, principal: Principal, data: PracticeCreate, *, queue: TaskQueue
) -> PracticeSession:
    student = await student_service.learner_for(db, principal, data.student_id)
    profile = student_service.class_profile(student)
    assert student.profile is not None

    count = data.count or profile.default_session_questions
    question_bank.check_count(profile, count)
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
    await question_bank.set_place(db, principal, session, data)
    db.add(session)
    await db.flush()

    owner = await student_service.account_of(db, student)
    reused = await question_bank.from_bank(db, owner, session, student, formats, count)
    _add_items(db, session, reused, 0)
    if len(reused) < count:
        llm.get_llm_provider()  # 503 now, rather than a failed session later, when AI is switched off
    else:
        session.status = "ready"
    await db.commit()
    if session.status == "preparing":
        await queue.enqueue(prepare_session, session_id=session.id)
    return session


async def _write_the_rest(
    db: AsyncSession, session: PracticeSession, student: Student, owner: uuid.UUID
) -> int:
    have = await db.scalar(select(func.count()).where(PracticeItem.session_id == session.id)) or 0
    formats = strategy.allowed_formats(student_service.class_profile(student), session.question_type)
    written = await question_bank.write(
        db, owner, session, student, formats=formats, count=session.question_count - have
    )
    _add_items(db, session, written, have)
    return have + len(written)


async def prepare_session(db: AsyncSession, *, session_id: uuid.UUID) -> None:
    """The background job that writes the questions a session still needs. Safe to run again."""
    await question_bank.prepare(db, PracticeSession, session_id, _write_the_rest)


async def resume_unfinished_sessions(
    session_factory: async_sessionmaker[AsyncSession], queue: TaskQueue
) -> None:
    """At start-up: sessions whose questions were being written when the server stopped are queued again."""
    for session_id in await question_bank.preparing(session_factory, PracticeSession):
        await queue.enqueue(prepare_session, session_id=session_id)


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
    db: AsyncSession, principal: Principal, session_id: uuid.UUID, data: AnswerIn, *, queue: TaskQueue
) -> AnswerResult:
    session = await get_session(db, principal, session_id)
    if session.status not in ("ready", "completed"):
        raise InvalidInputError("This practice is not ready yet.", code="practice_not_ready")
    item, question = await _item(db, session, data.question_id)
    student = await db.get(Student, session.student_id)
    assert student is not None and student.profile is not None
    profile = student_service.class_profile(student)

    response = data.model_dump(include={"option", "value", "text", "pairs"}, exclude_none=True)
    correct = checking.is_correct(question, response)
    feedback = None
    if correct is None:
        grade = await checking.mark_written(
            question, response["text"], profile=profile, student=student.profile
        )
        correct, feedback = grade.is_correct, grade.feedback

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
    await mastery.record_answer(db, student, question)
    examine = await misconceptions.after_answer(db, student, question)
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
        await recommendations.mark_done(db, session)
        await study_plan_service.practice_done(db, session)
    await db.commit()
    if examine:
        await queue.enqueue(
            misconceptions.examine,
            student_id=student.id,
            chapter_id=question.chapter_id,
            topic_id=question.topic_id,
        )

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
        profile=student_service.class_profile(student),
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
