"""Adaptive learning: student_mastery, recommendations, and practice for one topic.

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "student_mastery",
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("chapter_id", sa.Uuid(), nullable=False),
        sa.Column("topic_id", sa.Uuid(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("accuracy", sa.Float(), nullable=False),
        sa.Column("mastery", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("avg_time_ms", sa.Integer(), nullable=True),
        sa.Column("last_practised_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("difficulty", sa.String(length=8), nullable=True),
        sa.Column("difficulty_since", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["students.id"],
            name=op.f("fk_student_mastery_student_id_students"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["chapter_id"],
            ["chapters.id"],
            name=op.f("fk_student_mastery_chapter_id_chapters"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"], ["topics.id"], name=op.f("fk_student_mastery_topic_id_topics"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_student_mastery")),
        # One row per learner and area; a chapter-wide area has no topic, and NULLs count as equal.
        sa.UniqueConstraint(
            "student_id",
            "chapter_id",
            "topic_id",
            name=op.f("uq_student_mastery_student_id"),
            postgresql_nulls_not_distinct=True,
        ),
    )
    op.create_table(
        "recommendations",
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("chapter_id", sa.Uuid(), nullable=False),
        sa.Column("topic_id", sa.Uuid(), nullable=True),
        sa.Column("difficulty", sa.String(length=8), nullable=False),
        sa.Column("reason", sa.String(length=300), nullable=False),
        sa.Column("status", sa.String(length=8), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["students.id"],
            name=op.f("fk_recommendations_student_id_students"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["chapter_id"],
            ["chapters.id"],
            name=op.f("fk_recommendations_chapter_id_chapters"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"], ["topics.id"], name=op.f("fk_recommendations_topic_id_topics"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_recommendations")),
        sa.UniqueConstraint("student_id", "day", "position", name=op.f("uq_recommendations_student_id")),
    )
    op.add_column("practice_sessions", sa.Column("topic_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        op.f("fk_practice_sessions_topic_id_topics"),
        "practice_sessions",
        "topics",
        ["topic_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("fk_practice_sessions_topic_id_topics"), "practice_sessions", type_="foreignkey")
    op.drop_column("practice_sessions", "topic_id")
    op.drop_table("recommendations")
    op.drop_table("student_mastery")
