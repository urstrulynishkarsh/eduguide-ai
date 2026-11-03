"""Conversations with the Parent AI Assistant and the Student AI Tutor.

Who: the assistant is for a parent, about one of their children; the tutor is for a learner (a
child in child mode, or a student who signed up alone), and their parent may read it too. Anyone
else gets 404.

A message (`prepare_turn`, then `reply_events`):

    understand (small, fast call) -> search the child's books when needed -> stream the reply

The reply streams back as Server-Sent Events: `delta` (a piece of text), then `done` (the saved
question and reply, with the books the reply was based on) or `error`. The question and the reply
are saved together only when the reply is complete, so a failed reply leaves nothing half-done.
Logs carry ids and counts - never what anyone wrote.
"""

import json
import logging
import re
import textwrap
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from sqlalchemy import ColumnElement, select, true
from sqlalchemy.ext.asyncio import AsyncSession

from app import llm
from app.adaptive_learning import mastery
from app.analytics import progress
from app.auth.principal import Principal
from app.chat import assistant, tutor
from app.core.errors import AppError, NotFoundError, PermissionDeniedError
from app.llm import Message
from app.models import ChatMessage, ChatSession, Student
from app.models.base import utcnow
from app.rag import retrieval
from app.schemas.chat import ChatCreate, ChatKind, ChatMessageOut, ChatOut, ChatPage, ChatSummary
from app.services import dashboard_service, learn_service, library_service, student_service
from app.utils import pagination

logger = logging.getLogger(__name__)

HISTORY = 6  # earlier messages sent with each reply request
_HISTORY_CHARS = 2000  # of each of them
# A citation as models write it: "[S1]", "[S1, S2]", "[S1][S3]", "(see [S2])".
_TAGS = r"\[S\d+(?:\s*,\s*S\d+)*\](?:\s*\[S\d+(?:\s*,\s*S\d+)*\])*"
_CITATION = re.compile(rf"\s*\((?:see\s+)?{_TAGS}\)|\s*{_TAGS}", re.IGNORECASE)


def citations(reply: str) -> tuple[str, set[str]]:
    """The reply without its citations (the books are listed under it instead), and the tags it used."""
    used = {tag for match in _CITATION.finditer(reply) for tag in re.findall(r"S\d+", match.group())}
    return _CITATION.sub("", reply), used


def _visible(principal: Principal) -> ColumnElement[bool]:
    """A parent sees their children's conversations; a learner sees only their own tutor."""
    return student_service.visible_to(principal) & (
        true() if principal.is_parent else ChatSession.kind == "tutor"
    )


def _parent_only(principal: Principal, kind: ChatKind) -> None:
    if kind == "assistant" and not principal.is_parent:
        raise PermissionDeniedError("The assistant is for parents.", code="parent_required")


async def _session(db: AsyncSession, principal: Principal, chat_id: uuid.UUID) -> ChatSession:
    session = await db.scalar(
        select(ChatSession)
        .join(Student, Student.id == ChatSession.student_id)
        .where(ChatSession.id == chat_id, _visible(principal))
        .execution_options(populate_existing=True)
    )
    if session is None:
        raise NotFoundError("We couldn't find this conversation.", code="chat_not_found")
    return session


def _message_out(message: ChatMessage) -> ChatMessageOut:
    return ChatMessageOut.model_validate(message, from_attributes=True)


async def create_session(db: AsyncSession, principal: Principal, data: ChatCreate) -> ChatSummary:
    _parent_only(principal, data.kind)
    student = await student_service.learner_for(db, principal, data.student_id)
    session = ChatSession(student_id=student.id, kind=data.kind, title="")
    db.add(session)
    await db.commit()
    return ChatSummary.model_validate(session, from_attributes=True)


async def list_sessions(
    db: AsyncSession,
    principal: Principal,
    kind: ChatKind,
    student_id: uuid.UUID | None,
    *,
    limit: int,
    cursor: str | None,
) -> ChatPage:
    _parent_only(principal, kind)
    student = await student_service.learner_for(db, principal, student_id)
    query = select(ChatSession).where(ChatSession.student_id == student.id, ChatSession.kind == kind)
    sessions, next_cursor = await pagination.newest_first(db, query, ChatSession, limit=limit, cursor=cursor)
    return ChatPage(
        items=[ChatSummary.model_validate(s, from_attributes=True) for s in sessions], next_cursor=next_cursor
    )


async def _messages(db: AsyncSession, session: ChatSession) -> list[ChatMessage]:
    query = select(ChatMessage).where(ChatMessage.session_id == session.id).order_by(ChatMessage.created_at)
    return list((await db.scalars(query)).all())


async def get_session(db: AsyncSession, principal: Principal, chat_id: uuid.UUID) -> ChatOut:
    session = await _session(db, principal, chat_id)
    return ChatOut(
        **ChatSummary.model_validate(session, from_attributes=True).model_dump(),
        messages=[_message_out(message) for message in await _messages(db, session)],
    )


async def delete_session(db: AsyncSession, principal: Principal, chat_id: uuid.UUID) -> None:
    await db.delete(await _session(db, principal, chat_id))
    await db.commit()


# ---------------------------------------------------------------------------- a message and its reply


@dataclass
class Turn:
    session: ChatSession
    question: str
    system: str
    messages: list[Message]  # the conversation so far, then this turn's task
    passages: list[retrieval.Passage]
    rung: str | None = None  # tutor: the help this reply gives
    state: tutor.State | None = None  # tutor: the problem and its rung after this reply


def _history(messages: list[ChatMessage]) -> list[Message]:
    """The last few messages, the learner's or parent's own words marked as material."""
    history = []
    for message in messages[-HISTORY:]:
        content = message.content[:_HISTORY_CHARS]
        if message.role == "user":
            content = f"<message>{content}</message>"
        history.append(Message("user" if message.role == "user" else "assistant", content))
    return history


async def prepare_turn(db: AsyncSession, principal: Principal, chat_id: uuid.UUID, text: str) -> Turn:
    """Everything before the reply: understanding the message and searching the books. Raises the
    usual errors (503 when the AI is off, 422 when the books do not cover a problem) before any
    streaming starts."""
    session = await _session(db, principal, chat_id)
    provider = llm.get_llm_provider()
    student = student_service.require_profile(await db.get(Student, session.student_id))
    assert student.profile is not None
    profile = student_service.class_profile(student)
    earlier = await _messages(db, session)
    where = await learn_service.learner_books(db, await student_service.account_of(db, student), student)
    languages = await learn_service.book_languages(db, where)
    budget = provider.request_size.passage_tokens

    if session.kind == "assistant":
        understood = await assistant.understand(text, languages)
        passages = []
        if understood.on_topic and understood.needs_books and understood.search_query:
            passages = await learn_service.find_passages(
                db, where, understood.search_query, token_budget=budget
            )
        board = await dashboard_service.snapshot(db, student)
        areas = (await mastery.knowledge_profile(db, student)).areas
        facts = assistant.child_data(board, areas, await progress.progress(db, student.id))
        return Turn(
            session,
            text,
            assistant.system_prompt(profile, student.profile),
            [*_history(earlier), Message("user", assistant.task(understood, text, facts, passages))],
            passages,
        )

    state = tutor.State(session.problem, session.rung, session.hints_only)
    last_reply = next((m.content for m in reversed(earlier) if m.role == "assistant"), "")
    understood = await tutor.understand(text, state, last_reply, languages)
    step = tutor.next_step(state, understood, text)
    passages = []
    if step.reply in ("help", "check", "explain"):
        query = understood.search_query if understood.intent in ("new_problem", "concept") else None
        passages = await learn_service.find_passages(
            db, where, query or step.state.problem or text, token_budget=budget
        )
        if not passages:
            raise retrieval.InsufficientContextError()
    logger.info("Tutor %s: %s -> %s %s", session.id, understood.intent, step.reply, step.rung or "")
    return Turn(
        session,
        text,
        tutor.system_prompt(profile, student.profile),
        [
            *_history(earlier),
            Message("user", tutor.task(step, text, passages, student.profile.primary_language)),
        ],
        passages,
        step.rung,
        step.state,
    )


def _event(name: str, data: dict[str, Any]) -> str:
    return f"event: {name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def reply_events(db: AsyncSession, turn: Turn) -> AsyncIterator[str]:
    """The reply as Server-Sent Events; the question and the reply are saved when it is complete."""
    pieces: list[str] = []
    try:
        async for piece in llm.get_llm_provider().stream_text(system=turn.system, messages=turn.messages):
            pieces.append(piece)
            yield _event("delta", {"text": piece})
    except AppError as error:  # busy, unreachable, declined: what was sent is to be discarded
        yield _event("error", {"code": error.code, "message": error.message})
        return
    reply = "".join(pieces).strip()
    if not reply:
        yield _event("error", {"code": "ai_unavailable", "message": llm.AIUnavailableError.message})
        return

    content, used = citations(reply)
    cited = [p.chunk for p in turn.passages if p.tag in used]
    sources = await library_service.describe_sources(
        db, [(c.book_id, c.chapter_id, c.exercise_id, c.page_start) for c in cited]
    )
    now = utcnow()
    question = ChatMessage(
        session_id=turn.session.id, role="user", content=turn.question, sources=[], created_at=now
    )
    answer = ChatMessage(
        session_id=turn.session.id,
        role="assistant",
        content=content,
        sources=[source.model_dump(mode="json") for source in sources],
        rung=turn.rung,
        created_at=now + timedelta(milliseconds=1),  # always after its question
    )
    db.add_all([question, answer])
    session = turn.session
    if turn.state is not None:
        session.problem, session.rung, session.hints_only = (
            turn.state.problem,
            turn.state.rung,
            turn.state.hints_only,
        )
    if not session.title:
        session.title = textwrap.shorten(turn.question, 120, placeholder="…")
    session.updated_at = now
    await db.commit()
    yield _event(
        "done",
        {
            "question": _message_out(question).model_dump(mode="json"),
            "answer": _message_out(answer).model_dump(mode="json"),
        },
    )
