"""My Books: books, the files they are made of, and what was found inside them.

Ownership: books, documents and chunks carry `owner_user_id`; chapters, topics and exercises are
reached through their book. Deleting the account deletes all of it.
"""

import uuid
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Computed,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

# Size of the search vectors. Fixed by the search model (app/rag/embeddings.py); a different
# model needs a migration and `python -m scripts.reembed`.
EMBEDDING_DIMENSION = 768


class Book(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One entry in "My Books". Can be made of several files (NCERT ships one PDF per chapter)."""

    __tablename__ = "books"

    owner_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    # The child the book is for. Empty = the whole family. Removing the child keeps the book.
    student_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("students.id", ondelete="SET NULL"), index=True
    )
    title: Mapped[str] = mapped_column(String(200))
    material_type: Mapped[str] = mapped_column(String(32))
    class_level: Mapped[str] = mapped_column(String(16))
    board: Mapped[str] = mapped_column(String(16))
    subject: Mapped[str] = mapped_column(String(60))
    language: Mapped[str] = mapped_column(String(16))  # language the book is written in

    documents: Mapped[list["Document"]] = relationship(
        back_populates="book",
        lazy="selectin",
        order_by="Document.created_at",
        cascade="all, delete-orphan",
        passive_deletes=True,  # the database deletes the documents (ON DELETE CASCADE)
    )


class Document(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One uploaded file and its processing state."""

    __tablename__ = "documents"
    __table_args__ = (
        # The same file twice in one book is refused (duplicate check by content hash).
        UniqueConstraint("book_id", "sha256", name="uq_documents_book_id_sha256"),
    )

    book_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), index=True)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    file_kind: Mapped[str] = mapped_column(String(8))
    mime_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    sha256: Mapped[str] = mapped_column(String(64))
    # Random name inside the private storage folder. Never derived from the uploaded file name.
    storage_key: Mapped[str] = mapped_column(String(200), unique=True)
    page_count: Mapped[int | None] = mapped_column(Integer)

    status: Mapped[str] = mapped_column(String(16), index=True)
    stage: Mapped[str | None] = mapped_column(String(32))  # the stage running now, or the one that failed
    error_code: Mapped[str | None] = mapped_column(String(64))
    attempts: Mapped[int] = mapped_column(SmallInteger, default=0, server_default=text("0"))
    processing_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    processing_finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Counts found while reading: pages, chapters, exercises, questions, chunks, pages read by OCR...
    stats: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"))

    book: Mapped[Book] = relationship(back_populates="documents", lazy="raise")


class Chapter(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "chapters"

    book_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), index=True)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    number: Mapped[int | None] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(300))
    position: Mapped[int] = mapped_column(Integer)  # order inside its document
    page_start: Mapped[int | None] = mapped_column(Integer)
    page_end: Mapped[int | None] = mapped_column(Integer)
    # How it was found: "outline" (PDF bookmarks), "heading", or "file" (the whole file is one chapter).
    detected_by: Mapped[str] = mapped_column(String(16))

    topics: Mapped[list["Topic"]] = relationship(
        lazy="raise", order_by="Topic.position", passive_deletes=True
    )
    exercises: Mapped[list["Exercise"]] = relationship(
        lazy="raise", order_by="Exercise.position", passive_deletes=True
    )


class Topic(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A section or concept inside a chapter, e.g. "2.3 Solving Equations"."""

    __tablename__ = "topics"

    chapter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chapters.id", ondelete="CASCADE"), index=True)
    number: Mapped[str | None] = mapped_column(String(16))
    title: Mapped[str] = mapped_column(String(300))
    position: Mapped[int] = mapped_column(Integer)
    page_start: Mapped[int | None] = mapped_column(Integer)


class Exercise(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An exercise block, e.g. "Exercise 2.3". `label` is empty for a plain "Exercises" heading."""

    __tablename__ = "exercises"

    chapter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chapters.id", ondelete="CASCADE"), index=True)
    label: Mapped[str] = mapped_column(String(32))
    position: Mapped[int] = mapped_column(Integer)
    page_start: Mapped[int | None] = mapped_column(Integer)
    page_end: Mapped[int | None] = mapped_column(Integer)
    question_count: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))


class DocumentChunk(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A labelled piece of book text: the unit that is searched and given to the AI.

    Class, board, subject and language are copied from the book so that search can filter on
    them in the same query that ranks by similarity (docs/02-database-schema.md).
    """

    __tablename__ = "document_chunks"
    __table_args__ = (
        Index("ix_document_chunks_owner_book", "owner_user_id", "book_id"),
        Index("ix_document_chunks_document_position", "document_id", "position"),
        Index("ix_document_chunks_search_text", "search_text", postgresql_using="gin"),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    owner_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    book_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"))
    chapter_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("chapters.id", ondelete="CASCADE"), index=True
    )
    topic_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("topics.id", ondelete="CASCADE"), index=True
    )
    exercise_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("exercises.id", ondelete="CASCADE"), index=True
    )
    content_type: Mapped[str] = mapped_column(String(24))
    content: Mapped[str] = mapped_column(Text)
    # One line placed in front of the text when it is embedded (Step 3), e.g.
    # "Class 8 · Mathematics · Chapter 2 Linear Equations · Exercise 2.3 · Question 4".
    context_label: Mapped[str] = mapped_column(String(400))
    page_start: Mapped[int | None] = mapped_column(Integer)
    page_end: Mapped[int | None] = mapped_column(Integer)
    position: Mapped[int] = mapped_column(Integer)  # reading order inside the document
    token_count: Mapped[int] = mapped_column(Integer)  # an estimate
    class_level: Mapped[str] = mapped_column(String(16))
    board: Mapped[str] = mapped_column(String(16))
    subject: Mapped[str] = mapped_column(String(60))
    language: Mapped[str] = mapped_column(String(16))
    # Extra labels, e.g. {"question_number": "4"} or {"example_number": "5"}.
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"))

    # Search (Step 3). The vector is compared exactly inside the filtered set (one family, usually
    # one book), so no approximate index is needed for correctness.
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIMENSION))
    embedding_model: Mapped[str | None] = mapped_column(String(100))
    # Keyword search catches exact things like "2.3" or a formula. 'simple' = no stemming, so
    # Hindi and English words are matched as written.
    search_text: Mapped[str] = mapped_column(
        TSVECTOR, Computed("to_tsvector('simple', context_label || ' ' || content)", persisted=True)
    )
