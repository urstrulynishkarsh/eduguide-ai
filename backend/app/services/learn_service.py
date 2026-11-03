"""Explaining a concept from the child's own books, with sources.

    question -> understand -> filter (family, visible books, class) -> embed -> search
    -> enough? -> context -> grounded explanation -> sources

When the books do not cover the question, the answer is `insufficient_context` - never a guess.
Logs carry ids, counts, scores and timings only.
"""

import logging
import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import llm
from app.auth.principal import Principal
from app.class_profiles import get_class_profile
from app.core.enums import ClassLevel
from app.models import Book, Student
from app.rag import answering, embeddings, retrieval
from app.schemas.learn import ExplainRequest, ExplainResponse
from app.services import library_service, student_service

logger = logging.getLogger(__name__)


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
    owner = principal.user.id
    book_ids = (
        await db.scalars(select(Book.id).where(library_service.books_for_learner(owner, student.id)))
    ).all()
    assert student.profile is not None
    return retrieval.ChunkFilter(owner, book_ids=book_ids, class_level=student.profile.class_level)


async def explain(db: AsyncSession, principal: Principal, data: ExplainRequest) -> ExplainResponse:
    llm.get_llm_provider()  # fail fast (503) before any work when AI is switched off
    student = await student_service.learner_for(db, principal, data.student_id)
    profile = student.profile
    assert profile is not None
    where = await _filter(db, principal, student, data)

    languages = set((await db.scalars(select(Book.language).where(Book.id.in_(where.book_ids or [])))).all())
    understood = await answering.understand(data.question, book_languages=languages)
    if not understood.on_topic:
        raise retrieval.InsufficientContextError()

    started = time.perf_counter()
    embedder = embeddings.get_embedding_provider()
    vector = await embedder.embed_query(understood.search_query)
    found = await retrieval.search(db, query_vector=vector, query_text=understood.search_query, where=where)
    best = max((passage.similarity for passage in found), default=0.0)
    logger.info(
        "Explain: %d candidates, best similarity %.3f, retrieval %.0f ms",
        len(found),
        best,
        (time.perf_counter() - started) * 1000,
    )
    if best < embedder.min_similarity:
        raise retrieval.InsufficientContextError()

    passages = retrieval.build_context(found)
    answer = await answering.explain(
        data.question,
        passages=passages,
        profile=get_class_profile(ClassLevel(profile.class_level)),
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
