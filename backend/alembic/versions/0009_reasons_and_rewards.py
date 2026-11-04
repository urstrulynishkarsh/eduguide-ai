"""Languages and rewards: the reasons of recommendations and study plan tasks become a code with its
numbers (JSON) instead of an English sentence, so the screens can word them in any language; the
rewards tables student_rewards (XP, streak) and student_badges.

Today's recommendations are made again on the next visit, so they are removed. A plan task keeps its
place; its old sentence becomes the general "planned" reason.

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def _learner(table: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["student_id"], ["students.id"], name=op.f(f"fk_{table}_student_id_students"), ondelete="CASCADE"
    )


def upgrade() -> None:
    op.execute("DELETE FROM recommendations")
    op.alter_column(
        "recommendations",
        "reason",
        type_=postgresql.JSONB(astext_type=sa.Text()),
        postgresql_using='\'{"code": "new_chapter"}\'::jsonb',
    )
    op.alter_column(
        "study_plan_items",
        "reason",
        type_=postgresql.JSONB(astext_type=sa.Text()),
        postgresql_using='\'{"code": "planned"}\'::jsonb',
    )

    counter = {"server_default": sa.text("0"), "nullable": False}
    op.create_table(
        "student_rewards",
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("xp", sa.Integer(), **counter),
        sa.Column("right_answers", sa.Integer(), **counter),
        sa.Column("streak", sa.SmallInteger(), **counter),
        sa.Column("longest_streak", sa.SmallInteger(), **counter),
        sa.Column("last_active_on", sa.Date(), nullable=True),
        sa.Column("day_answers", sa.SmallInteger(), **counter),
        *_timestamps(),
        _learner("student_rewards"),
        sa.PrimaryKeyConstraint("student_id", name=op.f("pk_student_rewards")),
    )
    op.create_table(
        "student_badges",
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("badge", sa.String(length=24), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        *_timestamps(),
        _learner("student_badges"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_student_badges")),
        sa.UniqueConstraint("student_id", "badge", name=op.f("uq_student_badges_student_id")),
    )


def downgrade() -> None:
    op.drop_table("student_badges")
    op.drop_table("student_rewards")
    for table in ("recommendations", "study_plan_items"):
        op.alter_column(table, "reason", type_=sa.String(length=300), postgresql_using="reason->>'code'")
