"""Learners and their learning profile."""

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, SmallInteger, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.user import Parent


class Student(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A learner. Belongs to exactly one account:

    * `parent_id` set  -> a child added by a parent (no login of their own)
    * `user_id` set    -> a student who signed up alone
    """

    __tablename__ = "students"
    __table_args__ = (
        CheckConstraint("num_nonnulls(parent_id, user_id) = 1", name="exactly_one_owner"),
        CheckConstraint("age IS NULL OR age BETWEEN 2 AND 25", name="age_range"),
    )

    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("parents.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    age: Mapped[int | None] = mapped_column(SmallInteger)

    parent: Mapped[Parent | None] = relationship(lazy="raise")
    profile: Mapped["StudentProfile | None"] = relationship(
        back_populates="student",
        uselist=False,
        lazy="joined",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    @property
    def has_own_login(self) -> bool:
        return self.user_id is not None


class StudentProfile(TimestampMixin, Base):
    """What the learner studies. The whole AI experience is driven from `class_level`."""

    __tablename__ = "student_profiles"

    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), primary_key=True
    )
    class_level: Mapped[str] = mapped_column(String(16))
    board: Mapped[str] = mapped_column(String(16))
    board_name: Mapped[str | None] = mapped_column(String(80))  # e.g. "MP Board" when board is state/other
    medium: Mapped[str] = mapped_column(String(16))  # medium of instruction at school
    primary_language: Mapped[str] = mapped_column(String(16))  # language the AI uses with this learner
    stream: Mapped[str | None] = mapped_column(String(16))  # Class 11-12 only
    goal: Mapped[str] = mapped_column(String(32))
    subjects: Mapped[list[str]] = mapped_column(JSONB, default=list, server_default=text("'[]'::jsonb"))

    student: Mapped[Student] = relationship(back_populates="profile", lazy="raise")
