"""Practice: questions, practice_sessions, practice_items, question_attempts.

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "practice_sessions",
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("book_id", sa.Uuid(), nullable=True),
        sa.Column("chapter_id", sa.Uuid(), nullable=True),
        sa.Column("exercise_id", sa.Uuid(), nullable=True),
        sa.Column("question_count", sa.SmallInteger(), nullable=False),
        sa.Column("difficulty", sa.String(length=8), nullable=False),
        sa.Column("question_type", sa.String(length=24), nullable=False),
        sa.Column("language", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["book_id"], ["books.id"], name=op.f("fk_practice_sessions_book_id_books"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["chapter_id"],
            ["chapters.id"],
            name=op.f("fk_practice_sessions_chapter_id_chapters"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["exercise_id"],
            ["exercises.id"],
            name=op.f("fk_practice_sessions_exercise_id_exercises"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["students.id"],
            name=op.f("fk_practice_sessions_student_id_students"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_practice_sessions")),
    )
    op.create_index(
        op.f("ix_practice_sessions_student_id"), "practice_sessions", ["student_id"], unique=False
    )
    op.create_table(
        "questions",
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("book_id", sa.Uuid(), nullable=False),
        sa.Column("chapter_id", sa.Uuid(), nullable=True),
        sa.Column("topic_id", sa.Uuid(), nullable=True),
        sa.Column("exercise_id", sa.Uuid(), nullable=True),
        sa.Column("origin", sa.String(length=16), nullable=False),
        sa.Column("class_level", sa.String(length=16), nullable=False),
        sa.Column("subject", sa.String(length=60), nullable=False),
        sa.Column("format", sa.String(length=24), nullable=False),
        sa.Column("style", sa.String(length=24), nullable=False),
        sa.Column("difficulty", sa.String(length=8), nullable=False),
        sa.Column("language", sa.String(length=16), nullable=False),
        sa.Column("body", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("answer", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("hints", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("solution", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_chunk_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("page", sa.Integer(), nullable=True),
        sa.Column("validation", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["book_id"], ["books.id"], name=op.f("fk_questions_book_id_books"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["chapter_id"], ["chapters.id"], name=op.f("fk_questions_chapter_id_chapters"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["exercise_id"],
            ["exercises.id"],
            name=op.f("fk_questions_exercise_id_exercises"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["owner_user_id"], ["users.id"], name=op.f("fk_questions_owner_user_id_users"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"], ["topics.id"], name=op.f("fk_questions_topic_id_topics"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_questions")),
    )
    op.create_index(op.f("ix_questions_book_id"), "questions", ["book_id"], unique=False)
    op.create_index(op.f("ix_questions_exercise_id"), "questions", ["exercise_id"], unique=False)
    op.create_index("ix_questions_owner_chapter", "questions", ["owner_user_id", "chapter_id"], unique=False)
    op.create_table(
        "practice_items",
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("hints_shown", sa.SmallInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("steps_shown", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("answer_shown", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["questions.id"],
            name=op.f("fk_practice_items_question_id_questions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["practice_sessions.id"],
            name=op.f("fk_practice_items_session_id_practice_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("session_id", "question_id", name=op.f("pk_practice_items")),
    )
    op.create_index(op.f("ix_practice_items_question_id"), "practice_items", ["question_id"], unique=False)
    op.create_table(
        "question_attempts",
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column("practice_session_id", sa.Uuid(), nullable=False),
        sa.Column("response", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("time_taken_ms", sa.Integer(), nullable=True),
        sa.Column("hints_used", sa.SmallInteger(), nullable=False),
        sa.Column("solution_viewed", sa.Boolean(), nullable=False),
        sa.Column("difficulty", sa.String(length=8), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["practice_session_id"],
            ["practice_sessions.id"],
            name=op.f("fk_question_attempts_practice_session_id_practice_sessions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["questions.id"],
            name=op.f("fk_question_attempts_question_id_questions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["students.id"],
            name=op.f("fk_question_attempts_student_id_students"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_question_attempts")),
    )
    op.create_index(
        op.f("ix_question_attempts_practice_session_id"),
        "question_attempts",
        ["practice_session_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_question_attempts_question_id"), "question_attempts", ["question_id"], unique=False
    )
    op.create_index(
        "ix_question_attempts_student_created",
        "question_attempts",
        ["student_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_question_attempts_student_created", table_name="question_attempts")
    op.drop_index(op.f("ix_question_attempts_question_id"), table_name="question_attempts")
    op.drop_index(op.f("ix_question_attempts_practice_session_id"), table_name="question_attempts")
    op.drop_table("question_attempts")
    op.drop_index(op.f("ix_practice_items_question_id"), table_name="practice_items")
    op.drop_table("practice_items")
    op.drop_index("ix_questions_owner_chapter", table_name="questions")
    op.drop_index(op.f("ix_questions_exercise_id"), table_name="questions")
    op.drop_index(op.f("ix_questions_book_id"), table_name="questions")
    op.drop_table("questions")
    op.drop_index(op.f("ix_practice_sessions_student_id"), table_name="practice_sessions")
    op.drop_table("practice_sessions")
