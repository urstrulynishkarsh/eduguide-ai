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
from app.class_profiles import get_class_profile
from app.core.enums import ClassLevel
from app.core.errors import InvalidInputError
from app.models import Book, Chapter, Exercise, Student
from app.rag import answering, embeddings, retrieval
from app.rag.ingestion.labels import chapter_label
from app.schemas.learn import ExplainRequest, ExplainResponse
from app.schemas.library import Source
from app.services import library_service, student_service

logger = logging.getLogger(__name__)


async def _learner(db: AsyncSession, principal: Principal, student_id: uuid.UUID | None) -> Student:
    if principal.student is not None:
        student = principal.student
    elif student_id is None:
        raise InvalidInputError(
            "Please choose which child this is for.",
            details=[{"field": "student_id", "message": "Choose a child."}],
        )
    else:
        student = await student_service.get_student(db, principal, student_id)
    if student.profile is None:
        raise InvalidInputError("Please fill in the class details first.", code="profile_required")
    return student


async def _filter(
    db: AsyncSession, principal: Principal, data: ExplainRequest, class_level: str
) -> retrieval.ChunkFilter:
    """Only books this session may see; only the learner's class unless a book or chapter is chosen."""
    if data.chapter_id is not None:
        chapter = await library_service.get_chapter(db, principal, data.chapter_id)  # 404 if not visible
        return retrieval.ChunkFilter(principal.user.id, book_ids=[chapter.book_id], chapter_id=chapter.id)
    if data.book_id is not None:
        book = await library_service.get_book(db, principal, data.book_id)
        return retrieval.ChunkFilter(principal.user.id, book_ids=[book.id])
    book_ids = (await db.scalars(select(Book.id).where(library_service.book_visible_to(principal)))).all()
    return retrieval.ChunkFilter(principal.user.id, book_ids=book_ids, class_level=class_level)


async def _sources(db: AsyncSession, passages: list[retrieval.Passage]) -> list[Source]:
    chunks = [passage.chunk for passage in passages]
    books = {b.id: b for b in await db.scalars(select(Book).where(Book.id.in_({c.book_id for c in chunks})))}
    chapters = {
        c.id: c
        for c in await db.scalars(select(Chapter).where(Chapter.id.in_({c.chapter_id for c in chunks})))
    }
    exercises = {
        e.id: e
        for e in await db.scalars(select(Exercise).where(Exercise.id.in_({c.exercise_id for c in chunks})))
    }
    sources = []
    for chunk in chunks:
        chapter = chapters.get(chunk.chapter_id)
        exercise = exercises.get(chunk.exercise_id)
        sources.append(
            Source(
                book_id=chunk.book_id,
                book_title=books[chunk.book_id].title,
                chapter=chapter_label(chapter.number, chapter.title) if chapter else None,
                exercise=(exercise.label or None) if exercise else None,
                page=chunk.page_start,
            )
        )
    return sources


async def explain(db: AsyncSession, principal: Principal, data: ExplainRequest) -> ExplainResponse:
    llm.get_llm_provider()  # fail fast (503) before any work when AI is switched off
    student = await _learner(db, principal, data.student_id)
    profile = student.profile
    assert profile is not None
    where = await _filter(db, principal, data, profile.class_level)

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
        sources=await _sources(db, cited),
    )
