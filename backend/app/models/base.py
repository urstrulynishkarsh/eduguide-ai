"""Base class and shared columns for all database tables."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Fixed names for indexes and constraints, so migrations are predictable.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)

    # Read any database-generated value back in the same statement, so it never
    # needs a second, lazy query (which is not allowed with async sessions).
    __mapper_args__ = {"eager_defaults": True}  # noqa: RUF012 - the shape SQLAlchemy expects


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)


def utcnow() -> datetime:
    return datetime.now(UTC)


class TimestampMixin:
    """`created_at` / `updated_at`, set by the application.

    The application clock is used (not the database's `now()`) because `now()`
    is frozen for the length of a transaction: two rows saved in the same
    transaction would get the same time and could not be put in order.
    The database default stays as a safety net for rows inserted by hand.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, server_default=func.now()
    )
