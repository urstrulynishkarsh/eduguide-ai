"""Mock tests and study plans: mock_tests, mock_test_questions, test_attempts, study_plans,
study_plan_items; test answers in question_attempts.

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def _fk(table: str, column: str, target: str, ondelete: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        [column], [f"{target}.id"], name=op.f(f"fk_{table}_{column}_{target}"), ondelete=ondelete
    )


def upgrade() -> None:
    op.create_table(
        "mock_tests",
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("book_id", sa.Uuid(), nullable=True),
        sa.Column("chapter_id", sa.Uuid(), nullable=True),
        sa.Column("topic_id", sa.Uuid(), nullable=True),
        sa.Column("exercise_id", sa.Uuid(), nullable=True),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("question_count", sa.SmallInteger(), nullable=False),
        sa.Column("difficulty", sa.String(length=8), nullable=False),
        sa.Column("language", sa.String(length=16), nullable=False),
        sa.Column("duration_minutes", sa.SmallInteger(), nullable=True),
        sa.Column("sections", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        *_timestamps(),
        _fk("mock_tests", "student_id", "students", "CASCADE"),
        _fk("mock_tests", "book_id", "books", "SET NULL"),
        _fk("mock_tests", "chapter_id", "chapters", "SET NULL"),
        _fk("mock_tests", "topic_id", "topics", "SET NULL"),
        _fk("mock_tests", "exercise_id", "exercises", "SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mock_tests")),
    )
    op.create_index(op.f("ix_mock_tests_student_id"), "mock_tests", ["student_id"])
    op.create_table(
        "mock_test_questions",
        sa.Column("mock_test_id", sa.Uuid(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column("section", sa.String(length=1), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("marks", sa.SmallInteger(), nullable=False),
        _fk("mock_test_questions", "mock_test_id", "mock_tests", "CASCADE"),
        _fk("mock_test_questions", "question_id", "questions", "CASCADE"),
        sa.PrimaryKeyConstraint("mock_test_id", "question_id", name=op.f("pk_mock_test_questions")),
    )
    op.create_index(op.f("ix_mock_test_questions_question_id"), "mock_test_questions", ["question_id"])
    op.create_table(
        "test_attempts",
        sa.Column("mock_test_id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "responses",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("score", sa.Float(), nullable=True),
        *_timestamps(),
        _fk("test_attempts", "mock_test_id", "mock_tests", "CASCADE"),
        _fk("test_attempts", "student_id", "students", "CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_test_attempts")),
    )
    op.create_index(op.f("ix_test_attempts_mock_test_id"), "test_attempts", ["mock_test_id"])

    # A test answer is a question attempt too, so progress and mastery count it.
    op.add_column("question_attempts", sa.Column("test_attempt_id", sa.Uuid(), nullable=True))
    op.add_column("question_attempts", sa.Column("marks", sa.Float(), nullable=True))
    op.alter_column("question_attempts", "practice_session_id", existing_type=sa.Uuid(), nullable=True)
    op.create_index(op.f("ix_question_attempts_test_attempt_id"), "question_attempts", ["test_attempt_id"])
    op.create_foreign_key(
        op.f("fk_question_attempts_test_attempt_id_test_attempts"),
        "question_attempts",
        "test_attempts",
        ["test_attempt_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_check_constraint(
        op.f("ck_question_attempts_practice_or_test"),
        "question_attempts",
        "num_nonnulls(practice_session_id, test_attempt_id) = 1",
    )

    op.create_table(
        "study_plans",
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("exam_date", sa.Date(), nullable=False),
        sa.Column("daily_minutes", sa.SmallInteger(), nullable=False),
        sa.Column("target_score", sa.SmallInteger(), nullable=False),
        sa.Column(
            "chapter_ids", postgresql.ARRAY(sa.Uuid()), server_default=sa.text("'{}'::uuid[]"), nullable=False
        ),
        sa.Column("planned_on", sa.Date(), nullable=False),
        sa.Column("unscheduled", sa.SmallInteger(), nullable=False),
        *_timestamps(),
        _fk("study_plans", "student_id", "students", "CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_study_plans")),
        # One plan per learner: their daily minutes can only be planned once.
        sa.UniqueConstraint("student_id", name=op.f("uq_study_plans_student_id")),
    )
    op.create_table(
        "study_plan_items",
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("book_id", sa.Uuid(), nullable=False),
        sa.Column("chapter_id", sa.Uuid(), nullable=True),
        sa.Column("topic_id", sa.Uuid(), nullable=True),
        sa.Column("difficulty", sa.String(length=8), nullable=False),
        sa.Column("minutes", sa.SmallInteger(), nullable=False),
        sa.Column("reason", sa.String(length=300), nullable=False),
        sa.Column("status", sa.String(length=8), nullable=False),
        *_timestamps(),
        _fk("study_plan_items", "plan_id", "study_plans", "CASCADE"),
        _fk("study_plan_items", "book_id", "books", "CASCADE"),
        _fk("study_plan_items", "chapter_id", "chapters", "CASCADE"),
        _fk("study_plan_items", "topic_id", "topics", "CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_study_plan_items")),
    )
    op.create_index("ix_study_plan_items_plan_day", "study_plan_items", ["plan_id", "day"])


def downgrade() -> None:
    op.drop_table("study_plan_items")
    op.drop_table("study_plans")
    # Test answers cannot exist without their tests.
    op.execute("DELETE FROM question_attempts WHERE test_attempt_id IS NOT NULL")
    op.drop_constraint(op.f("ck_question_attempts_practice_or_test"), "question_attempts", type_="check")
    op.drop_constraint(
        op.f("fk_question_attempts_test_attempt_id_test_attempts"), "question_attempts", type_="foreignkey"
    )
    op.drop_index(op.f("ix_question_attempts_test_attempt_id"), table_name="question_attempts")
    op.alter_column("question_attempts", "practice_session_id", existing_type=sa.Uuid(), nullable=False)
    op.drop_column("question_attempts", "marks")
    op.drop_column("question_attempts", "test_attempt_id")
    op.drop_table("test_attempts")
    op.drop_table("mock_test_questions")
    op.drop_table("mock_tests")
