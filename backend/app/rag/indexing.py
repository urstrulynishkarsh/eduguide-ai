"""Keeping chunk vectors up to date.

A chunk needs (re-)embedding when it has no vector yet, when its label changed (a parent renamed
a chapter - `embedding_model` is cleared then), or when the search model changed. One job covers
all three; `python -m scripts.reembed` runs it for every book.
"""

import logging
import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DocumentChunk
from app.rag import embeddings
from app.rag.ingestion.labels import embedding_text

logger = logging.getLogger(__name__)

_BATCH = 64


async def embed_stale_chunks(db: AsyncSession, *, book_id: uuid.UUID | None = None) -> int:
    """Embed every stale chunk (of one book, or of all books). Returns how many were embedded."""
    embedder = embeddings.get_embedding_provider()
    query = (
        select(DocumentChunk.id, DocumentChunk.context_label, DocumentChunk.content)
        .where(DocumentChunk.embedding_model.is_distinct_from(embedder.model_name))
        .order_by(DocumentChunk.id)
        .limit(_BATCH)
    )
    if book_id is not None:
        query = query.where(DocumentChunk.book_id == book_id)

    done = 0
    while rows := (await db.execute(query)).all():
        vectors = await embedder.embed_passages(
            [embedding_text(row.context_label, row.content) for row in rows]
        )
        await db.execute(
            update(DocumentChunk),
            [
                {"id": row.id, "embedding": vector, "embedding_model": embedder.model_name}
                for row, vector in zip(rows, vectors, strict=True)
            ],
        )
        await db.commit()
        done += len(rows)
    if done:
        logger.info("Embedded %d chunk(s)%s", done, f" of book {book_id}" if book_id else "")
    return done
