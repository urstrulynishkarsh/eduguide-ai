"""Previous-year paper analysis: what was read from each paper of a "Previous-year papers" book.

A paper is one file (document) of the book; reading it found its sections and questions (rag/ingestion,
question-paper mode). The analysis adds what the AI read: the paper's year, time and negative marking,
and for every question its marks, its format and the chapter and topic of the family's textbooks that
teach it. Rows go with the file and its questions; a removed textbook leaves its questions unmatched.
"""

import uuid

from sqlalchemy import Float, ForeignKey, SmallInteger, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class PaperAnalysis(TimestampMixin, Base):
    """One paper of the book, as analysed. Made again each time the book is analysed."""

    __tablename__ = "paper_analyses"

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True
    )
    book_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(16))  # preparing | ready | failed
    error_code: Mapped[str | None] = mapped_column(String(64))
    year: Mapped[int | None] = mapped_column(SmallInteger)
    duration_minutes: Mapped[int | None] = mapped_column(SmallInteger)
    # Marks lost for a wrong objective answer, as the paper's instructions say (0: none).
    negative_marks: Mapped[float] = mapped_column(Float, default=0, server_default=text("0"))


class PaperQuestion(Base):
    """One question of an analysed paper (an exercise question of the paper's text)."""

    __tablename__ = "paper_questions"

    chunk_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_chunks.id", ondelete="CASCADE"), primary_key=True
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("paper_analyses.document_id", ondelete="CASCADE"), index=True
    )
    marks: Mapped[float | None] = mapped_column(Float)  # for a right answer; empty when not printed
    format: Mapped[str] = mapped_column(String(24))
    # Where the family's textbooks of the paper's class teach it; empty: none of them does.
    chapter_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("chapters.id", ondelete="SET NULL"))
    topic_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("topics.id", ondelete="SET NULL"))
