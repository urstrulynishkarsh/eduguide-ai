"""Conversations with the Parent AI Assistant and the Student AI Tutor.

A conversation is about one learner (the assistant's parent asks about that child; the tutor talks
with that learner) and goes with them. A question and its reply are stored together, once the reply
is complete.
"""

import uuid
from typing import Any

from sqlalchemy import Boolean, ForeignKey, Index, SmallInteger, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ChatSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "chat_sessions"

    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(16))  # assistant | tutor
    title: Mapped[str] = mapped_column(String(120))  # the first question, shortened ("" before it)
    # The tutor's problem in hand and how far up the hint ladder it has gone (app/chat/tutor.py).
    problem: Mapped[str | None] = mapped_column(Text)
    rung: Mapped[int | None] = mapped_column(SmallInteger)  # position in tutor.LADDER of the last help
    hints_only: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))


class ChatMessage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "chat_messages"
    __table_args__ = (Index("ix_chat_messages_session_created", "session_id", "created_at"),)

    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chat_sessions.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(16))  # user | assistant
    content: Mapped[str] = mapped_column(Text)
    # The books a reply was based on: [{book_id, book_title, chapter, exercise, page}]
    sources: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, default=list, server_default=text("'[]'::jsonb")
    )
    rung: Mapped[str | None] = mapped_column(String(16))  # tutor replies: the help given (hint_1 … answer)
