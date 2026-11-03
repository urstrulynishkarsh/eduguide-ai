"""My Books: books, chapters and exercises.

Every query in this file starts from the caller's account (`owner_user_id`), taken from the
verified token. Something that belongs to another family is answered with 404, never 403.

Who may do what:
* a parent - everything with their family's books;
* a student who signed up alone - the same, for their own books;
* a child in child mode - read the family's books that are for everyone or for them, but not
  add, change or delete anything.
"""

import base64
import binascii
import logging
import uuid
from collections.abc import Sequence
from datetime import datetime
from enum import Enum

from sqlalchemy import ColumnElement, Select, and_, func, or_, select, tuple_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.principal import Principal
from app.core.config import get_settings
from app.core.enums import ClassLevel, ContentType, Role
from app.core.errors import ConflictError, InvalidInputError, NotFoundError, PermissionDeniedError
from app.core.tasks import TaskQueue
from app.models import Book, Chapter, Document, DocumentChunk, Exercise, Topic
from app.rag.indexing import embed_stale_chunks
from app.rag.ingestion.labels import build_context_label, chapter_label
from app.schemas.library import BookCreate, BookUpdate, ChapterUpdate, Source
from app.services import student_service
from app.storage import FileStorage

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------- access rules


def is_child_mode(principal: Principal) -> bool:
    """A parent's account acting as one child."""
    return principal.role is Role.STUDENT and principal.user.role == Role.PARENT


def book_visible_to(principal: Principal) -> ColumnElement[bool]:
    condition = Book.owner_user_id == principal.user.id
    if is_child_mode(principal):
        condition = and_(condition, or_(Book.student_id.is_(None), Book.student_id == principal.student_id))
    return condition


def books_for_learner(owner_user_id: uuid.UUID, student_id: uuid.UUID) -> ColumnElement[bool]:
    """The family's shared books and this learner's own - not a sibling's."""
    return and_(
        Book.owner_user_id == owner_user_id, or_(Book.student_id.is_(None), Book.student_id == student_id)
    )


def ensure_can_manage(principal: Principal) -> None:
    """Parents, and students who signed up alone, manage their books. Child mode only reads."""
    if is_child_mode(principal):
        raise PermissionDeniedError("Only a parent can change the library.", code="parent_required")


# ---------------------------------------------------------------------------- books


async def get_book(db: AsyncSession, principal: Principal, book_id: uuid.UUID) -> Book:
    book = await db.scalar(
        select(Book)
        .where(Book.id == book_id, book_visible_to(principal))
        .execution_options(populate_existing=True)
    )
    if book is None:
        raise NotFoundError("We couldn't find this book.", code="book_not_found")
    return book


async def chapter_counts(db: AsyncSession, book_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    if not book_ids:
        return {}
    rows = await db.execute(
        select(Chapter.book_id, func.count()).where(Chapter.book_id.in_(book_ids)).group_by(Chapter.book_id)
    )
    return {book_id: count for book_id, count in rows}


def _encode_cursor(book: Book) -> str:
    raw = f"{book.created_at.isoformat()}|{book.id}".encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    try:
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)).decode()
        created, book_id = raw.split("|")
        return datetime.fromisoformat(created), uuid.UUID(book_id)
    except (ValueError, binascii.Error, UnicodeDecodeError):
        raise InvalidInputError(
            "This page link is not valid.",
            code="invalid_cursor",
            details=[{"field": "cursor", "message": "Invalid cursor."}],
        ) from None


async def list_books(
    db: AsyncSession, principal: Principal, *, limit: int, cursor: str | None, student_id: uuid.UUID | None
) -> tuple[list[Book], str | None]:
    """Newest first. `student_id` narrows the list to books for that child (plus family books)."""
    query = select(Book).where(book_visible_to(principal))
    if student_id is not None:
        query = query.where(or_(Book.student_id.is_(None), Book.student_id == student_id))
    if cursor:
        created, book_id = _decode_cursor(cursor)
        query = query.where(tuple_(Book.created_at, Book.id) < tuple_(created, book_id))
    rows = list(
        (await db.scalars(query.order_by(Book.created_at.desc(), Book.id.desc()).limit(limit + 1))).all()
    )
    next_cursor = _encode_cursor(rows[limit - 1]) if len(rows) > limit else None
    return rows[:limit], next_cursor


async def create_book(db: AsyncSession, principal: Principal, data: BookCreate) -> Book:
    ensure_can_manage(principal)

    limit = get_settings().max_books_per_account
    count = await db.scalar(
        select(func.count()).select_from(Book).where(Book.owner_user_id == principal.user.id)
    )
    if (count or 0) >= limit:
        raise ConflictError(f"You can have up to {limit} books.", code="book_limit_reached")

    student_id = data.student_id
    if student_id is None and principal.student_id is not None:
        student_id = principal.student_id  # a student who signed up alone: their own book
    profile = None
    if student_id is not None:
        student = await student_service.get_student(db, principal, student_id)  # 404 if not ours
        profile = student.profile

    class_level = data.class_level or (ClassLevel(profile.class_level) if profile else None)
    if class_level is None:
        raise InvalidInputError(
            "Please choose the class this book is for.",
            details=[{"field": "class_level", "message": "Choose the class this book is for."}],
        )
    board = data.board.value if data.board else (profile.board if profile else "other")
    language = data.language or (profile.medium if profile and profile.medium != "other" else "en")

    book = Book(
        owner_user_id=principal.user.id,
        student_id=student_id,
        title=data.title,
        subject=data.subject,
        material_type=data.material_type.value,
        class_level=class_level.value,
        board=board,
        language=language,
        documents=[],
    )
    db.add(book)
    await db.commit()
    return book


async def update_book(
    db: AsyncSession, principal: Principal, book_id: uuid.UUID, data: BookUpdate, *, queue: TaskQueue
) -> Book:
    ensure_can_manage(principal)
    book = await get_book(db, principal, book_id)
    changes = data.model_dump(exclude_unset=True)
    if "student_id" in changes and changes["student_id"] is not None:
        await student_service.get_student(db, principal, changes["student_id"])  # 404 if not ours

    for field, value in changes.items():
        setattr(book, field, value.value if isinstance(value, Enum) else value)

    # Chunks keep copies of these for fast filtering; keep them in step with the book.
    copied = {
        field: getattr(book, field) for field in ("class_level", "board", "subject") if field in changes
    }
    if copied:
        await db.execute(update(DocumentChunk).where(DocumentChunk.book_id == book.id).values(**copied))
        await refresh_context_labels(db, book)
    await db.commit()
    if copied:
        await queue.enqueue(embed_stale_chunks, book_id=book.id)
    return book


async def delete_book(
    db: AsyncSession, principal: Principal, book_id: uuid.UUID, storage: FileStorage
) -> None:
    """Deletes the book, its files and everything found in them."""
    ensure_can_manage(principal)
    book = await get_book(db, principal, book_id)
    keys = [document.storage_key for document in book.documents]
    await db.delete(book)
    await db.commit()
    for key in keys:
        try:
            await storage.delete(key)
        except OSError:
            logger.warning("Could not delete a stored file of book %s", book_id, exc_info=True)


# ---------------------------------------------------------------------------- chapters


def _chapter_query(principal: Principal) -> Select[tuple[Chapter]]:
    return select(Chapter).join(Book, Book.id == Chapter.book_id).where(book_visible_to(principal))


async def list_chapters(db: AsyncSession, principal: Principal, book_id: uuid.UUID) -> list[Chapter]:
    book = await get_book(db, principal, book_id)
    result = await db.scalars(
        _chapter_query(principal)
        .join(Document, Document.id == Chapter.document_id)
        .where(Chapter.book_id == book.id)
        .order_by(Chapter.number.asc().nulls_last(), Document.created_at, Chapter.position)
    )
    return list(result.all())


async def get_chapter(db: AsyncSession, principal: Principal, chapter_id: uuid.UUID) -> Chapter:
    chapter = await db.scalar(
        _chapter_query(principal).where(Chapter.id == chapter_id).execution_options(populate_existing=True)
    )
    if chapter is None:
        raise NotFoundError("We couldn't find this chapter.", code="chapter_not_found")
    return chapter


async def chapter_details(db: AsyncSession, chapter_ids: list[uuid.UUID]) -> dict[uuid.UUID, dict[str, int]]:
    """Counts per chapter: topics, exercises, questions, examples, summaries."""
    details = {
        chapter_id: {"topics": 0, "exercises": 0, "questions": 0, "examples": 0, "summaries": 0}
        for chapter_id in chapter_ids
    }
    if not chapter_ids:
        return details
    for chapter_id, count in await db.execute(
        select(Topic.chapter_id, func.count())
        .where(Topic.chapter_id.in_(chapter_ids))
        .group_by(Topic.chapter_id)
    ):
        details[chapter_id]["topics"] = count
    for chapter_id, count, questions in await db.execute(
        select(Exercise.chapter_id, func.count(), func.coalesce(func.sum(Exercise.question_count), 0))
        .where(Exercise.chapter_id.in_(chapter_ids))
        .group_by(Exercise.chapter_id)
    ):
        details[chapter_id]["exercises"] = count
        details[chapter_id]["questions"] = int(questions)
    for chapter_id, content_type, count in await db.execute(
        select(DocumentChunk.chapter_id, DocumentChunk.content_type, func.count())
        .where(
            DocumentChunk.chapter_id.in_(chapter_ids),
            DocumentChunk.content_type.in_([ContentType.EXAMPLE.value, ContentType.SUMMARY.value]),
        )
        .group_by(DocumentChunk.chapter_id, DocumentChunk.content_type)
    ):
        key = "examples" if content_type == ContentType.EXAMPLE.value else "summaries"
        details[chapter_id][key] = count
    return details


async def chapter_contents(db: AsyncSession, chapter: Chapter) -> tuple[list[Topic], list[Exercise]]:
    topics = await db.scalars(select(Topic).where(Topic.chapter_id == chapter.id).order_by(Topic.position))
    exercises = await db.scalars(
        select(Exercise).where(Exercise.chapter_id == chapter.id).order_by(Exercise.position)
    )
    return list(topics.all()), list(exercises.all())


async def update_chapter(
    db: AsyncSession, principal: Principal, chapter_id: uuid.UUID, data: ChapterUpdate, *, queue: TaskQueue
) -> Chapter:
    ensure_can_manage(principal)
    chapter = await get_chapter(db, principal, chapter_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(chapter, field, value)
    book = await db.get(Book, chapter.book_id)
    assert book is not None
    await db.flush()
    await refresh_context_labels(db, book, chapter_id=chapter.id)
    await db.commit()
    await queue.enqueue(embed_stale_chunks, book_id=book.id)
    return chapter


# ---------------------------------------------------------------------------- exercises


async def get_exercise(
    db: AsyncSession, principal: Principal, exercise_id: uuid.UUID
) -> tuple[Exercise, Chapter, Book]:
    row = (
        await db.execute(
            select(Exercise, Chapter, Book)
            .join(Chapter, Chapter.id == Exercise.chapter_id)
            .join(Book, Book.id == Chapter.book_id)
            .where(Exercise.id == exercise_id, book_visible_to(principal))
        )
    ).first()
    if row is None:
        raise NotFoundError("We couldn't find this exercise.", code="exercise_not_found")
    exercise, chapter, book = row
    return exercise, chapter, book


async def exercise_questions(db: AsyncSession, exercise: Exercise) -> list[DocumentChunk]:
    result = await db.scalars(
        select(DocumentChunk)
        .where(
            DocumentChunk.exercise_id == exercise.id,
            DocumentChunk.content_type == ContentType.EXERCISE_QUESTION.value,
        )
        .order_by(DocumentChunk.position)
    )
    return list(result.all())


# ---------------------------------------------------------------------------- sources


async def describe_sources(
    db: AsyncSession, refs: Sequence[tuple[uuid.UUID, uuid.UUID | None, uuid.UUID | None, int | None]]
) -> list[Source]:
    """(book_id, chapter_id, exercise_id, page) -> "Based on: Class 8 Mathematics, Chapter 2 ..." (§42)."""
    books = {b.id: b for b in await db.scalars(select(Book).where(Book.id.in_({r[0] for r in refs})))}
    chapters = {
        c.id: c for c in await db.scalars(select(Chapter).where(Chapter.id.in_({r[1] for r in refs})))
    }
    exercises = {
        e.id: e for e in await db.scalars(select(Exercise).where(Exercise.id.in_({r[2] for r in refs})))
    }
    sources = []
    for book_id, chapter_id, exercise_id, page in refs:
        chapter, exercise = chapters.get(chapter_id), exercises.get(exercise_id)
        sources.append(
            Source(
                book_id=book_id,
                book_title=books[book_id].title,
                chapter=chapter_label(chapter.number, chapter.title) if chapter else None,
                exercise=(exercise.label or None) if exercise else None,
                page=page,
            )
        )
    return sources


# ---------------------------------------------------------------------------- labels


async def refresh_context_labels(
    db: AsyncSession, book: Book, *, chapter_id: uuid.UUID | None = None
) -> None:
    """Rebuild chunk labels after the book or a chapter was renamed or re-classified.

    The label is part of what is embedded, so the vectors are marked stale (`embedding_model`
    cleared); the caller queues `embed_stale_chunks` after committing."""
    chunk_query = select(
        DocumentChunk.id,
        DocumentChunk.chapter_id,
        DocumentChunk.topic_id,
        DocumentChunk.exercise_id,
        DocumentChunk.content_type,
        DocumentChunk.meta,
    ).where(DocumentChunk.book_id == book.id)
    chapter_query = select(Chapter).where(Chapter.book_id == book.id)
    if chapter_id is not None:
        chunk_query = chunk_query.where(DocumentChunk.chapter_id == chapter_id)
        chapter_query = chapter_query.where(Chapter.id == chapter_id)

    chapters = {chapter.id: chapter for chapter in (await db.scalars(chapter_query)).all()}
    chapter_ids = list(chapters)
    topics = {
        topic.id: topic
        for topic in (await db.scalars(select(Topic).where(Topic.chapter_id.in_(chapter_ids)))).all()
    }
    exercises = {
        exercise.id: exercise
        for exercise in (await db.scalars(select(Exercise).where(Exercise.chapter_id.in_(chapter_ids)))).all()
    }
    updates = [
        {
            "id": row.id,
            "context_label": build_context_label(
                class_level=book.class_level,
                subject=book.subject,
                chapter=chapters.get(row.chapter_id),
                topic=topics.get(row.topic_id),
                exercise=exercises.get(row.exercise_id),
                content_type=row.content_type,
                meta=row.meta,
            ),
            "embedding_model": None,
        }
        for row in (await db.execute(chunk_query)).all()
    ]
    if updates:
        await db.execute(update(DocumentChunk), updates)
