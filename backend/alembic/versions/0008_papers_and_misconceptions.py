"""Previous-year paper analysis, misconceptions and exam patterns: paper_analyses, paper_questions,
student_misconceptions; mock_tests.exam; student_mastery.examined_until.

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def _foreign_key(table: str, column: str, target: str, ondelete: str) -> sa.ForeignKeyConstraint:
    referred = target.split(".")[0]
    return sa.ForeignKeyConstraint(
        [column], [target], name=op.f(f"fk_{table}_{column}_{referred}"), ondelete=ondelete
    )


def upgrade() -> None:
    op.create_table(
        "paper_analyses",
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("book_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("year", sa.SmallInteger(), nullable=True),
        sa.Column("duration_minutes", sa.SmallInteger(), nullable=True),
        sa.Column("negative_marks", sa.Float(), server_default=sa.text("0"), nullable=False),
        *_timestamps(),
        _foreign_key("paper_analyses", "document_id", "documents.id", "CASCADE"),
        _foreign_key("paper_analyses", "book_id", "books.id", "CASCADE"),
        sa.PrimaryKeyConstraint("document_id", name=op.f("pk_paper_analyses")),
    )
    op.create_index(op.f("ix_paper_analyses_book_id"), "paper_analyses", ["book_id"])
    op.create_table(
        "paper_questions",
        sa.Column("chunk_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("marks", sa.Float(), nullable=True),
        sa.Column("format", sa.String(length=24), nullable=False),
        sa.Column("chapter_id", sa.Uuid(), nullable=True),
        sa.Column("topic_id", sa.Uuid(), nullable=True),
        _foreign_key("paper_questions", "chunk_id", "document_chunks.id", "CASCADE"),
        _foreign_key("paper_questions", "document_id", "paper_analyses.document_id", "CASCADE"),
        _foreign_key("paper_questions", "chapter_id", "chapters.id", "SET NULL"),
        _foreign_key("paper_questions", "topic_id", "topics.id", "SET NULL"),
        sa.PrimaryKeyConstraint("chunk_id", name=op.f("pk_paper_questions")),
    )
    op.create_index(op.f("ix_paper_questions_document_id"), "paper_questions", ["document_id"])
    op.create_table(
        "student_misconceptions",
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("chapter_id", sa.Uuid(), nullable=False),
        sa.Column("topic_id", sa.Uuid(), nullable=True),
        sa.Column("pattern", sa.String(length=300), nullable=False),
        sa.Column("fix", sa.String(length=500), nullable=False),
        sa.Column("explain_question", sa.String(length=300), nullable=False),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=8), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        *_timestamps(),
        _foreign_key("student_misconceptions", "student_id", "students.id", "CASCADE"),
        _foreign_key("student_misconceptions", "chapter_id", "chapters.id", "CASCADE"),
        _foreign_key("student_misconceptions", "topic_id", "topics.id", "CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_student_misconceptions")),
    )
    op.create_index(op.f("ix_student_misconceptions_student_id"), "student_misconceptions", ["student_id"])
    op.add_column("mock_tests", sa.Column("exam", sa.String(length=8), nullable=True))
    op.add_column("student_mastery", sa.Column("examined_until", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("student_mastery", "examined_until")
    op.drop_column("mock_tests", "exam")
    op.drop_table("student_misconceptions")
    op.drop_table("paper_questions")
    op.drop_table("paper_analyses")
