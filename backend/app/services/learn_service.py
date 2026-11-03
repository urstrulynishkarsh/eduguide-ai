"""Explaining a concept from the child's own books, with sources.

    question -> understand -> filter (family, visible books, class) -> embed -> search
    -> enough? -> context -> grounded explanation -> sources

When the books do not cover the question, the answer is `insufficient_context` - never a guess.
Logs carry ids, counts, scores and timings only.
"""

import logging
import time
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import llm
from app.auth.principal import Principal
from app.models import Book, Student
from app.rag import answering, embeddings, retrieval
from app.schemas.learn import ExplainRequest, ExplainResponse
from app.services import library_service, student_service

logger = logging.getLogger(__name__)


async def learner_books(db: AsyncSession, owner: uuid.UUID, student: Student) -> retrieval.ChunkFilter:
    """Every book of the learner's class that they may use (the family's and their own)."""
    book_ids = (
        await db.scalars(select(Book.id).where(library_service.books_for_learner(owner, student.id)))
    ).all()
    assert student.profile is not None
    return retrieval.ChunkFilter(owner, book_ids=book_ids, class_level=student.profile.class_level)


async def book_languages(db: AsyncSession, where: retrieval.ChunkFilter) -> set[str]:
    return set((await db.scalars(select(Book.language).where(Book.id.in_(where.book_ids or [])))).all())


async def find_passages(
    db: AsyncSession,
    where: retrieval.ChunkFilter,
    query: str,
    *,
    token_budget: int = retrieval.CONTEXT_TOKEN_BUDGET,
) -> list[retrieval.Passage]:
    """The passages that answer `query`, tagged S1, S2...; none when the books do not cover it."""
    started = time.perf_counter()
    embedder = embeddings.get_embedding_provider()
    vector = await embedder.embed_query(query)
    found = await retrieval.search(db, query_vector=vector, query_text=query, where=where)
    best = max((passage.similarity for passage in found), default=0.0)
    logger.info(
        "Search: %d candidates, best similarity %.3f, %.0f ms",
        len(found),
        best,
        (time.perf_counter() - started) * 1000,
    )
    if best < embedder.min_similarity:
        return []
    return retrieval.build_context(found, token_budget)


async def _filter(
    db: AsyncSession, principal: Principal, student: Student, data: ExplainRequest
) -> retrieval.ChunkFilter:
    """A chosen chapter or book (if this session may see it); otherwise the learner's books of their class."""
    if data.chapter_id is not None:
        chapter = await library_service.get_chapter(db, principal, data.chapter_id)  # 404 if not visible
        return retrieval.ChunkFilter(principal.user.id, book_ids=[chapter.book_id], chapter_id=chapter.id)
    if data.book_id is not None:
        book = await library_service.get_book(db, principal, data.book_id)
        return retrieval.ChunkFilter(principal.user.id, book_ids=[book.id])
    return await learner_books(db, principal.user.id, student)


async def explain(db: AsyncSession, principal: Principal, data: ExplainRequest) -> ExplainResponse:
    llm.get_llm_provider()  # fail fast (503) before any work when AI is switched off
    student = await student_service.learner_for(db, principal, data.student_id)
    profile = student.profile
    assert profile is not None
    where = await _filter(db, principal, student, data)

    understood = await answering.understand(data.question, book_languages=await book_languages(db, where))
    if not understood.on_topic:
        raise retrieval.InsufficientContextError()
    passages = await find_passages(db, where, understood.search_query)
    if not passages:
        raise retrieval.InsufficientContextError()

    answer = await answering.explain(
        data.question,
        passages=passages,
        profile=student_service.class_profile(student),
        student=profile,
        style=data.style,
    )
    if not answer.enough_information:
        raise retrieval.InsufficientContextError()

    cited = [passage for passage in passages if passage.tag in answer.sources_used]
    return ExplainResponse(
        explanation=answer.explanation,
        steps=answer.steps,
        style=data.style,
        sources=await library_service.describe_sources(
            db,
            [(p.chunk.book_id, p.chunk.chapter_id, p.chunk.exercise_id, p.chunk.page_start) for p in cited],
        ),
    )
