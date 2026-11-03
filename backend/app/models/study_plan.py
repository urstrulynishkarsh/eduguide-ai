"""Study plans: one per learner, from today to an exam, made of daily tasks.

The tasks of the remaining days are planned again each day from what the learner knows
(services/study_plan_service.py, adaptive_learning/planner.py). Tasks point at real books, chapters
and topics, so a deleted book takes its tasks with it.
"""

import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Index, SmallInteger, String, Uuid, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class StudyPlan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "study_plans"

    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), unique=True)
    exam_date: Mapped[date] = mapped_column(Date)
    daily_minutes: Mapped[int] = mapped_column(SmallInteger)
    target_score: Mapped[int] = mapped_column(SmallInteger)  # percent
    # The chapters the exam covers; empty = every chapter of the learner's books for their class.
    chapter_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(Uuid), default=list, server_default=text("'{}'::uuid[]")
    )
    planned_on: Mapped[date] = mapped_column(Date)  # the day (India time) the rest was last planned
    unscheduled: Mapped[int] = mapped_column(SmallInteger)  # tasks that did not fit before the exam


class StudyPlanItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "study_plan_items"
    __table_args__ = (Index("ix_study_plan_items_plan_day", "plan_id", "day"),)

    plan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("study_plans.id", ondelete="CASCADE"))
    day: Mapped[date] = mapped_column(Date)
    position: Mapped[int] = mapped_column(SmallInteger)
    kind: Mapped[str] = mapped_column(String(16))  # learn | practice | test
    book_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"))
    # Empty for a test of the whole book; topic empty = the chapter in general.
    chapter_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("chapters.id", ondelete="CASCADE"))
    topic_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"))
    difficulty: Mapped[str] = mapped_column(String(8))  # easy | medium | hard | mixed
    minutes: Mapped[int] = mapped_column(SmallInteger)
    reason: Mapped[str] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(8))  # pending | done | skipped | missed
