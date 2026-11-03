"""Practice: the question bank, practice sessions, and every answer a learner gives.

Questions belong to the family (`owner_user_id`) and to the chapter they were written from, so a
saved question is reused by later sessions and tests instead of being generated again. Sessions
and attempts belong to one learner.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Question(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A practice question with its answer, hints and worked solution.

    `origin` is "generated" for questions the AI wrote (textbook questions are listed from the
    book itself, GET /exercises/{id}). The UI must never present a generated question as the book's.
    """

    __tablename__ = "questions"
    __table_args__ = (Index("ix_questions_owner_chapter", "owner_user_id", "chapter_id"),)

    owner_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    book_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), index=True)
    chapter_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("chapters.id", ondelete="CASCADE"))
    topic_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("topics.id", ondelete="SET NULL"))
    exercise_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("exercises.id", ondelete="SET NULL"), index=True
    )
    origin: Mapped[str] = mapped_column(String(16))
    class_level: Mapped[str] = mapped_column(String(16))
    subject: Mapped[str] = mapped_column(String(60))
    format: Mapped[str] = mapped_column(String(24))
    style: Mapped[str] = mapped_column(String(24))
    difficulty: Mapped[str] = mapped_column(String(8))  # easy | medium | hard
    language: Mapped[str] = mapped_column(String(16))
    # What is shown: {"text", "options"?, "case"?, "left"?, "right"?, "unit"?}
    body: Mapped[dict[str, Any]] = mapped_column(JSONB)
    # Never sent before the learner answers: {"option"} | {"value", "tolerance"} | {"accepted"} |
    # {"pairs"} | {"model_answer", "key_points"}
    answer: Mapped[dict[str, Any]] = mapped_column(JSONB)
    hints: Mapped[list[str]] = mapped_column(JSONB)
    solution: Mapped[dict[str, Any]] = mapped_column(JSONB)  # {"concept", "steps", "final_answer"}
    source_chunk_ids: Mapped[list[str]] = mapped_column(JSONB)  # the passages it was written from
    page: Mapped[int | None] = mapped_column(Integer)
    validation: Mapped[dict[str, Any]] = mapped_column(JSONB)  # what the independent check found


class QuestionSettings:
    """What a practice session or a mock test asks for (services/question_bank.py reads these).

    The place the questions come from is at most one of book, chapter, topic, exercise (the wider
    ones are filled in too); all empty = every book of the learner's class.
    """

    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    book_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("books.id", ondelete="SET NULL"))
    chapter_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("chapters.id", ondelete="SET NULL"))
    topic_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("topics.id", ondelete="SET NULL"))
    exercise_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("exercises.id", ondelete="SET NULL"))
    question_count: Mapped[int] = mapped_column(SmallInteger)  # asked for; the questions can be fewer
    difficulty: Mapped[str] = mapped_column(String(8))  # easy | medium | hard | mixed
    language: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16))  # preparing | ready | failed (practice: + completed)
    error_code: Mapped[str | None] = mapped_column(String(64))


class PracticeSession(QuestionSettings, UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "practice_sessions"

    question_type: Mapped[str] = mapped_column(String(24))  # a format, or "mixed"
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PracticeItem(Base):
    """One question in a session, and how much help the learner has opened for it."""

    __tablename__ = "practice_items"

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("practice_sessions.id", ondelete="CASCADE"), primary_key=True
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    position: Mapped[int] = mapped_column(SmallInteger)
    hints_shown: Mapped[int] = mapped_column(SmallInteger, default=0, server_default=text("0"))
    steps_shown: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    answer_shown: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))


class QuestionAttempt(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Every answer a learner gives, in a practice or a test - the raw material for progress and
    mastery."""

    __tablename__ = "question_attempts"
    __table_args__ = (
        Index("ix_question_attempts_student_created", "student_id", "created_at"),
        CheckConstraint("num_nonnulls(practice_session_id, test_attempt_id) = 1", name="practice_or_test"),
    )

    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"))
    question_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), index=True)
    # Exactly one of the two: the practice or the test the answer was given in.
    practice_session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("practice_sessions.id", ondelete="CASCADE"), index=True
    )
    test_attempt_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("test_attempts.id", ondelete="CASCADE"), index=True
    )
    marks: Mapped[float | None] = mapped_column(Float)  # tests only: the marks given
    response: Mapped[dict[str, Any]] = mapped_column(JSONB)
    is_correct: Mapped[bool] = mapped_column(Boolean)
    feedback: Mapped[str | None] = mapped_column(Text)  # from the AI, for written answers
    time_taken_ms: Mapped[int | None] = mapped_column(Integer)
    hints_used: Mapped[int] = mapped_column(SmallInteger)
    solution_viewed: Mapped[bool] = mapped_column(Boolean)
    difficulty: Mapped[str] = mapped_column(String(8))
