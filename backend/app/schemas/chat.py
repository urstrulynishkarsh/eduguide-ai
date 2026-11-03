"""Conversations: the Parent AI Assistant and the Student AI Tutor (hint first, answer last)."""

import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

from app.schemas.library import Source

ChatKind = Literal["assistant", "tutor"]
Rung = Literal["hint_1", "hint_2", "concept", "steps", "answer"]


class ChatCreate(BaseModel):
    kind: ChatKind = Field(description="assistant: a parent asking about a child · tutor: a learner's tutor.")
    student_id: uuid.UUID | None = Field(
        default=None, description="Which child (parents only). A student session always uses itself."
    )


class ChatMessageIn(BaseModel):
    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


class ChatMessageOut(BaseModel):
    id: uuid.UUID
    role: Literal["user", "assistant"]
    content: str
    sources: list[Source] = Field(description='Replies: the books they were based on ("Based on: …").')
    rung: Rung | None = Field(
        description="Tutor replies helping with a problem: how much help this was, on the ladder "
        "hint_1 → hint_2 → concept → steps → answer."
    )
    created_at: datetime


class ChatSummary(BaseModel):
    id: uuid.UUID
    student_id: uuid.UUID
    kind: ChatKind
    title: str = Field(description="The first question, shortened; empty before the first message.")
    created_at: datetime
    updated_at: datetime


class ChatOut(ChatSummary):
    messages: list[ChatMessageOut] = Field(description="Oldest first.")


class ChatPage(BaseModel):
    items: list[ChatSummary]
    next_cursor: str | None = Field(
        description="Pass as `cursor` to get the next page; null on the last page."
    )
