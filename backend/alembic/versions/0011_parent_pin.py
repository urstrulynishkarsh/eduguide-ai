"""The parent PIN, and child-mode sessions that last until a grown-up leaves them.

parents.pin_hash: the PIN that leaves child mode. auth_sessions.student_id: the child a child-mode
session acts as, so its tokens can be renewed as that child only. A child-mode session started before
this migration names no child: it has no refresh token and ends after its 12 hours, as before.

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("parents", sa.Column("pin_hash", sa.String(length=255), nullable=True))
    op.add_column("auth_sessions", sa.Column("student_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        op.f("fk_auth_sessions_student_id_students"),
        "auth_sessions",
        "students",
        ["student_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("fk_auth_sessions_student_id_students"), "auth_sessions", type_="foreignkey")
    op.drop_column("auth_sessions", "student_id")
    op.drop_column("parents", "pin_hash")
