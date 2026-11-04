"""Streaks, XP and badges: what a learner has earned (analytics/rewards.py has the rules).

Counted as the learner works, never worked out again from history, so a book deleted later takes no
XP, streak or badge away. Both go with the learner (ON DELETE CASCADE).
"""

import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, SmallInteger, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class StudentReward(TimestampMixin, Base):
    """A learner's running totals; made with their first answer."""

    __tablename__ = "student_rewards"

    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), primary_key=True
    )
    xp: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    right_answers: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))  # first time
    streak: Mapped[int] = mapped_column(SmallInteger, default=0, server_default=text("0"))  # days in a row
    longest_streak: Mapped[int] = mapped_column(SmallInteger, default=0, server_default=text("0"))
    last_active_on: Mapped[date | None] = mapped_column(Date)  # India time
    day_answers: Mapped[int] = mapped_column(SmallInteger, default=0, server_default=text("0"))  # that day


class StudentBadge(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A badge a learner has earned, once; `created_at` is when."""

    __tablename__ = "student_badges"
    __table_args__ = (UniqueConstraint("student_id", "badge"),)

    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"))
    badge: Mapped[str] = mapped_column(String(24))  # a code of analytics/rewards.BADGES
