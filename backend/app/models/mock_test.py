"""Mock tests: a paper of sections built from the question bank, and every sitting of it.

A test belongs to one learner, like a practice session. Answers are saved on the sitting while the
test is taken and become `question_attempts` rows (with marks) when it is submitted, so progress and
mastery count them like practice answers.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, SmallInteger, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.practice import QuestionSettings


class MockTest(QuestionSettings, UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "mock_tests"

    kind: Mapped[str] = mapped_column(String(16))  # practice | chapter | full_mock
    duration_minutes: Mapped[int | None] = mapped_column(SmallInteger)  # empty = untimed
    # The paper's plan: [{"code": "A", "title", "marks" (each), "count", "formats"}]
    sections: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)


class MockTestQuestion(Base):
    """One question of a paper: its section, place in the section and marks."""

    __tablename__ = "mock_test_questions"

    mock_test_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mock_tests.id", ondelete="CASCADE"), primary_key=True
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    section: Mapped[str] = mapped_column(String(1))
    position: Mapped[int] = mapped_column(SmallInteger)  # inside the section
    marks: Mapped[int] = mapped_column(SmallInteger)


class MockTestAttempt(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One sitting of a test. A retake is a new sitting of the same paper."""

    __tablename__ = "test_attempts"

    mock_test_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mock_tests.id", ondelete="CASCADE"), index=True
    )
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Saved while the test is taken, changeable until it is submitted:
    # {question_id: {"option" | "value" | "text" | "pairs", "time_taken_ms"?}}
    responses: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"))
    score: Mapped[float | None] = mapped_column(Float)  # marks, set when submitted
