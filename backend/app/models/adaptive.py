"""Adaptive learning: what a learner knows, and what they should do next.

Both are about an *area*: a topic of a chapter, or the chapter itself for questions that have no
topic. Rows go with the learner, the chapter or the topic they are about (ON DELETE CASCADE), so a
deleted book never leaves a recommendation pointing at nothing.
"""

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, SmallInteger, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class StudentMastery(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """How well a learner knows one area. Worked out again after every answer in it
    (adaptive_learning/mastery.py)."""

    __tablename__ = "student_mastery"
    __table_args__ = (
        UniqueConstraint("student_id", "chapter_id", "topic_id", postgresql_nulls_not_distinct=True),
    )

    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"))
    chapter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chapters.id", ondelete="CASCADE"))
    topic_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"))
    attempts: Mapped[int] = mapped_column(Integer)  # first answers in this area, all time
    accuracy: Mapped[float] = mapped_column(Float)  # share right in the last 10
    mastery: Mapped[float] = mapped_column(Float)  # 0-1
    confidence: Mapped[float] = mapped_column(Float)  # 0-1: how much evidence there is
    avg_time_ms: Mapped[int | None] = mapped_column(Integer)
    last_practised_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # The level of the next practice (easy | medium | hard); empty where the class has no
    # adaptive difficulty. `difficulty_since` is the last change: later answers decide the next one.
    difficulty: Mapped[str | None] = mapped_column(String(8))
    difficulty_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # The newest wrong answer already looked at for misconceptions; later ones are still to be.
    examined_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Recommendation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One of a learner's "do this next" for a day (at most three a day, `position` 0-2)."""

    __tablename__ = "recommendations"
    __table_args__ = (UniqueConstraint("student_id", "day", "position"),)

    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"))
    day: Mapped[date] = mapped_column(Date)  # in India time
    position: Mapped[int] = mapped_column(SmallInteger)
    kind: Mapped[str] = mapped_column(String(16))  # strengthen | continue | review | new_chapter
    chapter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chapters.id", ondelete="CASCADE"))
    topic_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"))
    difficulty: Mapped[str] = mapped_column(String(8))  # easy | medium | hard | mixed
    reason: Mapped[dict[str, Any]] = mapped_column(JSONB)  # schemas.adaptive.Reason
    status: Mapped[str] = mapped_column(String(8))  # active | done


class StudentMisconception(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A wrong idea a learner keeps showing in one area, found in their wrong answers
    (adaptive_learning/misconceptions.py). `resolved` once they answer that area right again."""

    __tablename__ = "student_misconceptions"

    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    chapter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chapters.id", ondelete="CASCADE"))
    topic_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"))
    pattern: Mapped[str] = mapped_column(String(300))  # "Adds the denominators when adding fractions."
    fix: Mapped[str] = mapped_column(String(500))  # what to remember instead
    explain_question: Mapped[str] = mapped_column(String(300))  # asked of "Explain this" to clear it up
    evidence: Mapped[list[str]] = mapped_column(JSONB)  # ids of the question attempts that showed it
    status: Mapped[str] = mapped_column(String(8))  # active | resolved
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))  # its newest wrong answer
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
