"""Accounts and learners: users, parents, students, student_profiles.

Revision ID: 0001
Revises:
Create Date: 2026-10-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("preferred_language", sa.String(length=16), server_default="en", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint("role IN ('parent', 'student')", name=op.f("ck_users_role_valid")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "parents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_parents_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_parents")),
        sa.UniqueConstraint("user_id", name=op.f("uq_parents_user_id")),
    )

    op.create_table(
        "students",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("age", sa.SmallInteger(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint("age IS NULL OR age BETWEEN 2 AND 25", name=op.f("ck_students_age_range")),
        # A learner is either a parent's child or a student with their own login - never both, never neither.
        sa.CheckConstraint(
            "num_nonnulls(parent_id, user_id) = 1", name=op.f("ck_students_exactly_one_owner")
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"], ["parents.id"], name=op.f("fk_students_parent_id_parents"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_students_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_students")),
        sa.UniqueConstraint("user_id", name=op.f("uq_students_user_id")),
    )
    op.create_index(op.f("ix_students_parent_id"), "students", ["parent_id"], unique=False)

    op.create_table(
        "student_profiles",
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("class_level", sa.String(length=16), nullable=False),
        sa.Column("board", sa.String(length=16), nullable=False),
        sa.Column("board_name", sa.String(length=80), nullable=True),
        sa.Column("medium", sa.String(length=16), nullable=False),
        sa.Column("primary_language", sa.String(length=16), nullable=False),
        sa.Column("stream", sa.String(length=16), nullable=True),
        sa.Column("goal", sa.String(length=32), nullable=False),
        sa.Column(
            "subjects",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["students.id"],
            name=op.f("fk_student_profiles_student_id_students"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("student_id", name=op.f("pk_student_profiles")),
    )


def downgrade() -> None:
    op.drop_table("student_profiles")
    op.drop_index(op.f("ix_students_parent_id"), table_name="students")
    op.drop_table("students")
    op.drop_table("parents")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
