"""Conversations: the Parent AI Assistant and the Student AI Tutor (hint first, answer last)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Response, status
from fastapi.responses import StreamingResponse

from app.api.deps import CurrentPrincipal, DbSession
from app.schemas.chat import ChatCreate, ChatKind, ChatMessageIn, ChatOut, ChatPage, ChatSummary
from app.services import chat_service

router = APIRouter(tags=["Assistant and tutor"])


@router.post(
    "/chat/sessions",
    response_model=ChatSummary,
    status_code=status.HTTP_201_CREATED,
    summary="New conversation",
)
async def create_session(data: ChatCreate, principal: CurrentPrincipal, db: DbSession) -> ChatSummary:
    """`assistant`: a parent asking about one child (parents only). `tutor`: a learner's tutor."""
    return await chat_service.create_session(db, principal, data)


@router.get("/chat/sessions", response_model=ChatPage, summary="Conversations")
async def list_sessions(
    principal: CurrentPrincipal,
    db: DbSession,
    kind: ChatKind,
    student_id: uuid.UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    cursor: str | None = None,
) -> ChatPage:
    """Newest first. Parents name the child; a student session always lists its own."""
    return await chat_service.list_sessions(db, principal, kind, student_id, limit=limit, cursor=cursor)


@router.get("/chat/sessions/{chat_id}", response_model=ChatOut, summary="A conversation")
async def get_session(chat_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession) -> ChatOut:
    return await chat_service.get_session(db, principal, chat_id)


@router.delete(
    "/chat/sessions/{chat_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Remove a conversation"
)
async def delete_session(chat_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession) -> Response:
    await chat_service.delete_session(db, principal, chat_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/chat/sessions/{chat_id}/messages",
    response_class=StreamingResponse,
    summary="Send a message; the reply streams back",
    responses={200: {"content": {"text/event-stream": {}}, "description": "Server-Sent Events."}},
)
async def send_message(
    chat_id: uuid.UUID, data: ChatMessageIn, principal: CurrentPrincipal, db: DbSession
) -> StreamingResponse:
    """The reply streams as Server-Sent Events: `delta` `{"text"}` pieces, then `done`
    `{"question", "answer"}` (both saved; the answer with its `sources` and, from the tutor, its
    `rung`) or `error` `{"code", "message"}` (nothing saved). Errors found before the reply starts -
    the AI off, the books not covering a problem - are ordinary JSON errors."""
    turn = await chat_service.prepare_turn(db, principal, chat_id, data.text)
    return StreamingResponse(
        chat_service.reply_events(db, turn),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
