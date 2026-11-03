"""Search inside books: pgvector, chunk embeddings and a keyword index.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    # 768 = intfloat/multilingual-e5-base. Changing the model means a new migration and a re-embed.
    op.add_column("document_chunks", sa.Column("embedding", Vector(768), nullable=True))
    op.add_column("document_chunks", sa.Column("embedding_model", sa.String(length=100), nullable=True))
    op.add_column(
        "document_chunks",
        sa.Column(
            "search_text",
            postgresql.TSVECTOR(),
            sa.Computed("to_tsvector('simple', context_label || ' ' || content)", persisted=True),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_document_chunks_search_text", "document_chunks", ["search_text"], postgresql_using="gin"
    )


def downgrade() -> None:
    op.drop_index("ix_document_chunks_search_text", table_name="document_chunks")
    op.drop_column("document_chunks", "search_text")
    op.drop_column("document_chunks", "embedding_model")
    op.drop_column("document_chunks", "embedding")
    op.execute("DROP EXTENSION IF EXISTS vector")
