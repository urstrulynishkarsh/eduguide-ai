"""Finding the right passages in a family's books (docs/05-rag-pipeline.md §5.4).

Search by meaning: vector search and keyword search, both inside the filtered set, merged by
rank (reciprocal rank fusion). Keyword search catches exact things such as "2.3" or a formula
that vectors miss. The filter always contains the owner - `ChunkFilter` cannot be made without it.

Reranking (stage 7) is "none" for now: the merged order is used. A cross-encoder can be added
behind this module if the retrieval evaluation (`python -m scripts.eval_retrieval`) shows a need.
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import ColumnElement, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import DocumentChunk

_CANDIDATES = 30  # from each of vector and keyword search
_RRF_K = 60
CONTEXT_TOKEN_BUDGET = 3000


class InsufficientContextError(AppError):
    status_code = 422
    code = "insufficient_context"
    message = "I couldn't find enough information in your uploaded material to answer this reliably."


@dataclass(frozen=True, slots=True)
class ChunkFilter:
    """Which chunks may be used. `owner_user_id` is required: there is no unfiltered search."""

    owner_user_id: uuid.UUID
    book_ids: Sequence[uuid.UUID] | None = None
    class_level: str | None = None
    chapter_id: uuid.UUID | None = None
    exercise_id: uuid.UUID | None = None

    def conditions(self) -> list[ColumnElement[bool]]:
        conditions = [DocumentChunk.owner_user_id == self.owner_user_id]
        if self.book_ids is not None:
            conditions.append(DocumentChunk.book_id.in_(self.book_ids))
        if self.class_level is not None:
            conditions.append(DocumentChunk.class_level == self.class_level)
        if self.chapter_id is not None:
            conditions.append(DocumentChunk.chapter_id == self.chapter_id)
        if self.exercise_id is not None:
            conditions.append(DocumentChunk.exercise_id == self.exercise_id)
        return conditions


@dataclass(slots=True)
class Passage:
    chunk: DocumentChunk
    similarity: float
    tag: str = ""  # "S1", "S2"... set by build_context


async def _keyword_query(db: AsyncSession, query_text: str) -> str:
    """'how to solve 2x + 4' -> 'how' | 'to' | 'solve' | '2x' | '4' (any word may match).

    Postgres splits the words, so Hindi is split the same way as the stored text.
    """
    lexemes = await db.scalar(
        text("SELECT tsvector_to_array(to_tsvector('simple', :query))"), {"query": query_text}
    )
    return " | ".join("'" + lexeme.replace("'", "''") + "'" for lexeme in lexemes or [])


async def search(
    db: AsyncSession, *, query_vector: list[float], query_text: str, where: ChunkFilter, limit: int = 8
) -> list[Passage]:
    """The best passages for a question, best first."""
    conditions = where.conditions()
    distance = DocumentChunk.embedding.cosine_distance(query_vector)
    by_vector = (
        await db.scalars(
            select(DocumentChunk.id)
            .where(*conditions, DocumentChunk.embedding.is_not(None))
            .order_by(distance)
            .limit(_CANDIDATES)
        )
    ).all()
    by_keyword: Sequence[uuid.UUID] = []
    if keywords := await _keyword_query(db, query_text):
        ts_query = func.to_tsquery("simple", keywords)
        by_keyword = (
            await db.scalars(
                select(DocumentChunk.id)
                .where(*conditions, DocumentChunk.search_text.op("@@")(ts_query))
                .order_by(func.ts_rank(DocumentChunk.search_text, ts_query).desc())
                .limit(_CANDIDATES)
            )
        ).all()

    scores: dict[uuid.UUID, float] = {}
    for ranking in (by_vector, by_keyword):
        for rank, chunk_id in enumerate(ranking):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1 / (_RRF_K + rank + 1)
    best = sorted(scores, key=scores.__getitem__, reverse=True)[:limit]
    if not best:
        return []

    rows = await db.execute(
        select(DocumentChunk, (1 - distance).label("similarity")).where(DocumentChunk.id.in_(best))
    )
    found = {chunk.id: Passage(chunk, float(similarity or 0.0)) for chunk, similarity in rows}
    return [found[chunk_id] for chunk_id in best]


def build_context(passages: list[Passage], token_budget: int = CONTEXT_TOKEN_BUDGET) -> list[Passage]:
    """Best passages that fit the budget, without repeats, back in book order, tagged S1, S2..."""
    chosen: list[Passage] = []
    seen: set[str] = set()
    used = 0
    for passage in passages:
        if passage.chunk.content in seen or used + passage.chunk.token_count > token_budget:
            continue
        seen.add(passage.chunk.content)
        used += passage.chunk.token_count
        chosen.append(passage)
    chosen.sort(key=lambda p: (str(p.chunk.document_id), p.chunk.position))
    for number, passage in enumerate(chosen, start=1):
        passage.tag = f"S{number}"
    return chosen
