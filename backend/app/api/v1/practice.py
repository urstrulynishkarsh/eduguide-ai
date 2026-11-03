"""Practice: Create Practice, do it (answer, help, explain), and the learner's progress."""

import uuid

from fastapi import APIRouter, status

from app.analytics.progress import progress
from app.api.deps import CurrentPrincipal, DbSession, Queue
from app.models import PracticeSession
from app.schemas.learn import ExplainResponse
from app.schemas.library import DocumentError
from app.schemas.practice import (
    AnswerIn,
    AnswerResult,
    ExplainQuestionIn,
    HelpIn,
    HelpOut,
    ItemView,
    PracticeCreate,
    ProgressOut,
    QuestionView,
    SessionOut,
)
from app.services import library_service, practice_service, question_bank, student_service

router = APIRouter(tags=["Practice"])


async def _session_out(db: DbSession, session: PracticeSession) -> SessionOut:
    rows = await practice_service.session_items(db, session)
    sources = await library_service.describe_sources(
        db, [(q.book_id, q.chapter_id, q.exercise_id, q.page) for _, q, _, _ in rows]
    )
    items = []
    for (item, question, attempts, correct), source in zip(rows, sources, strict=True):
        items.append(
            ItemView(
                question=QuestionView.of(question, item.position + 1, source),
                attempts=attempts,
                correct=correct,
                hints_shown=item.hints_shown,
                hints_total=len(question.hints),
                steps_shown=item.steps_shown,
                answer_shown=item.answer_shown,
            )
        )
    error = None
    if session.status == "failed" and session.error_code:
        error = DocumentError(
            code=session.error_code, message=question_bank.error_message(session.error_code)
        )
    return SessionOut(
        id=session.id,
        student_id=session.student_id,
        status=session.status,
        error=error,
        question_count=session.question_count,
        difficulty=session.difficulty,
        question_type=session.question_type,
        language=session.language,
        items=items,
        answered=sum(1 for item in items if item.attempts),
        correct=sum(1 for item in items if item.correct),
        created_at=session.created_at,
        completed_at=session.completed_at,
    )


@router.post(
    "/practice/sessions",
    response_model=SessionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create Practice",
)
async def create_session(
    data: PracticeCreate, principal: CurrentPrincipal, db: DbSession, queue: Queue
) -> SessionOut:
    """Number, difficulty, type, source and language (spec §18). Saved questions the learner has
    not seen are reused first; the rest are written and checked in the background - `status` is
    `preparing` until then. Every question is marked `origin: "generated"`."""
    session = await practice_service.create_session(db, principal, data, queue=queue)
    return await _session_out(db, session)


@router.get(
    "/practice/sessions/{session_id}", response_model=SessionOut, summary="A practice and its questions"
)
async def get_session(session_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession) -> SessionOut:
    """Questions never include their answers. Poll while `status` is `preparing`."""
    return await _session_out(db, await practice_service.get_session(db, principal, session_id))


@router.post(
    "/practice/sessions/{session_id}/answers", response_model=AnswerResult, summary="Answer a question"
)
async def answer(
    session_id: uuid.UUID, data: AnswerIn, principal: CurrentPrincipal, db: DbSession
) -> AnswerResult:
    """Every answer is saved, with the hints and steps opened before it. Written answers are
    marked by the AI tutor."""
    return await practice_service.answer(db, principal, session_id, data)


@router.post(
    "/practice/sessions/{session_id}/questions/{question_id}/help",
    response_model=HelpOut,
    summary="Hint · Show Steps · Show Answer",
)
async def help_with(
    session_id: uuid.UUID, question_id: uuid.UUID, data: HelpIn, principal: CurrentPrincipal, db: DbSession
) -> HelpOut:
    """Hints come one at a time, from a nudge to the method; steps and answer show the worked solution."""
    return await practice_service.help_with(db, principal, session_id, question_id, data.level)


@router.post(
    "/practice/sessions/{session_id}/questions/{question_id}/explain",
    response_model=ExplainResponse,
    summary="Explain this question simply, like I'm 10, in Hindi or Hinglish",
)
async def explain_question(
    session_id: uuid.UUID,
    question_id: uuid.UUID,
    data: ExplainQuestionIn,
    principal: CurrentPrincipal,
    db: DbSession,
) -> ExplainResponse:
    return await practice_service.explain_question(db, principal, session_id, question_id, data.style)


@router.get("/students/{student_id}/progress", response_model=ProgressOut, summary="Basic progress")
async def student_progress(student_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession) -> ProgressOut:
    """Questions answered, accuracy, time, help used, and accuracy by chapter and topic."""
    student = await student_service.get_student(db, principal, student_id)
    return await progress(db, student.id)
