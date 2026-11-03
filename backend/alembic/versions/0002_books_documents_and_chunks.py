"""My Books: books, documents, chapters, topics, exercises, document_chunks.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-03

The search columns of document_chunks (embedding, keyword index) are added in Step 3.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def _owner(table: str) -> list:
    """The `owner_user_id` column and its foreign key: the one-column isolation rule."""
    return [
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_user_id"], ["users.id"], name=op.f(f"fk_{table}_owner_user_id_users"), ondelete="CASCADE"
        ),
    ]


def _jsonb_object(name: str) -> sa.Column:
    return sa.Column(
        name, postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False
    )


def upgrade() -> None:
    op.create_table(
        "books",
        sa.Column("id", sa.Uuid(), nullable=False),
        *_owner("books"),
        sa.Column("student_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("material_type", sa.String(length=32), nullable=False),
        sa.Column("class_level", sa.String(length=16), nullable=False),
        sa.Column("board", sa.String(length=16), nullable=False),
        sa.Column("subject", sa.String(length=60), nullable=False),
        sa.Column("language", sa.String(length=16), nullable=False),
        *_timestamps(),
        # Removing a child keeps the family's books.
        sa.ForeignKeyConstraint(
            ["student_id"], ["students.id"], name=op.f("fk_books_student_id_students"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_books")),
    )
    op.create_index(op.f("ix_books_owner_user_id"), "books", ["owner_user_id"], unique=False)
    op.create_index(op.f("ix_books_student_id"), "books", ["student_id"], unique=False)

    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("book_id", sa.Uuid(), nullable=False),
        *_owner("documents"),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("file_kind", sa.String(length=8), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("storage_key", sa.String(length=200), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("stage", sa.String(length=32), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("attempts", sa.SmallInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processing_finished_at", sa.DateTime(timezone=True), nullable=True),
        _jsonb_object("stats"),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["book_id"], ["books.id"], name=op.f("fk_documents_book_id_books"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_documents")),
        sa.UniqueConstraint("book_id", "sha256", name="uq_documents_book_id_sha256"),
        sa.UniqueConstraint("storage_key", name=op.f("uq_documents_storage_key")),
    )
    op.create_index(op.f("ix_documents_book_id"), "documents", ["book_id"], unique=False)
    op.create_index(op.f("ix_documents_owner_user_id"), "documents", ["owner_user_id"], unique=False)
    op.create_index(op.f("ix_documents_status"), "documents", ["status"], unique=False)

    op.create_table(
        "chapters",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("book_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("page_start", sa.Integer(), nullable=True),
        sa.Column("page_end", sa.Integer(), nullable=True),
        sa.Column("detected_by", sa.String(length=16), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["book_id"], ["books.id"], name=op.f("fk_chapters_book_id_books"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name=op.f("fk_chapters_document_id_documents"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_chapters")),
    )
    op.create_index(op.f("ix_chapters_book_id"), "chapters", ["book_id"], unique=False)
    op.create_index(op.f("ix_chapters_document_id"), "chapters", ["document_id"], unique=False)

    op.create_table(
        "topics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("chapter_id", sa.Uuid(), nullable=False),
        sa.Column("number", sa.String(length=16), nullable=True),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("page_start", sa.Integer(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["chapter_id"], ["chapters.id"], name=op.f("fk_topics_chapter_id_chapters"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_topics")),
    )
    op.create_index(op.f("ix_topics_chapter_id"), "topics", ["chapter_id"], unique=False)

    op.create_table(
        "exercises",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("chapter_id", sa.Uuid(), nullable=False),
        sa.Column("label", sa.String(length=32), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("page_start", sa.Integer(), nullable=True),
        sa.Column("page_end", sa.Integer(), nullable=True),
        sa.Column("question_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["chapter_id"], ["chapters.id"], name=op.f("fk_exercises_chapter_id_chapters"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_exercises")),
    )
    op.create_index(op.f("ix_exercises_chapter_id"), "exercises", ["chapter_id"], unique=False)

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        *_owner("document_chunks"),
        sa.Column("book_id", sa.Uuid(), nullable=False),
        sa.Column("chapter_id", sa.Uuid(), nullable=True),
        sa.Column("topic_id", sa.Uuid(), nullable=True),
        sa.Column("exercise_id", sa.Uuid(), nullable=True),
        sa.Column("content_type", sa.String(length=24), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("context_label", sa.String(length=400), nullable=False),
        sa.Column("page_start", sa.Integer(), nullable=True),
        sa.Column("page_end", sa.Integer(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        # Copied from the book so search can filter without joins.
        sa.Column("class_level", sa.String(length=16), nullable=False),
        sa.Column("board", sa.String(length=16), nullable=False),
        sa.Column("subject", sa.String(length=60), nullable=False),
        sa.Column("language", sa.String(length=16), nullable=False),
        _jsonb_object("meta"),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name=op.f("fk_document_chunks_document_id_documents"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["book_id"], ["books.id"], name=op.f("fk_document_chunks_book_id_books"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["chapter_id"],
            ["chapters.id"],
            name=op.f("fk_document_chunks_chapter_id_chapters"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"], ["topics.id"], name=op.f("fk_document_chunks_topic_id_topics"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["exercise_id"],
            ["exercises.id"],
            name=op.f("fk_document_chunks_exercise_id_exercises"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_chunks")),
    )
    op.create_index("ix_document_chunks_owner_book", "document_chunks", ["owner_user_id", "book_id"])
    op.create_index("ix_document_chunks_document_position", "document_chunks", ["document_id", "position"])
    op.create_index(op.f("ix_document_chunks_chapter_id"), "document_chunks", ["chapter_id"], unique=False)
    op.create_index(op.f("ix_document_chunks_topic_id"), "document_chunks", ["topic_id"], unique=False)
    op.create_index(op.f("ix_document_chunks_exercise_id"), "document_chunks", ["exercise_id"], unique=False)


def downgrade() -> None:
    # Dropping a table drops its indexes too.
    op.drop_table("document_chunks")
    op.drop_table("exercises")
    op.drop_table("topics")
    op.drop_table("chapters")
    op.drop_table("documents")
    op.drop_table("books")
