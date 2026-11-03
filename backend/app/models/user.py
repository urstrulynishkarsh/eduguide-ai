"""Accounts: who can sign in."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A login. `role` is "parent" or "student" (a student who signed up alone)."""

    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role IN ('parent', 'student')", name="role_valid"),)

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)  # always stored lower-case
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(20))
    preferred_language: Mapped[str] = mapped_column(String(16), default="en", server_default="en")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Parent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Parent-only details of an account. Children point here."""

    __tablename__ = "parents"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
