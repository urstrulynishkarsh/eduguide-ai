"""Adaptive learning: what a learner knows, and what they should do next.

Both are about an *area*: a topic of a chapter, or the chapter itself for questions that have no
topic. Rows go with the learner, the chapter or the topic they are about (ON DELETE CASCADE), so a
deleted book never leaves a recommendation pointing at nothing.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, SmallInteger, String, UniqueConstraint
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
    reason: Mapped[str] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(8))  # active | done
