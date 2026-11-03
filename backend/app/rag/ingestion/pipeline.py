"""Reading one uploaded document from start to finish, as a background job.

    extract_text -> detect_chapters -> detect_exercises -> detect_topics -> make_chunks
    -> embed_chunks -> ready

Each stage is saved on the `documents` row before it starts, so the progress checklist can be
polled. Everything the job produces is written in one transaction at the end; running the job
again first deletes what an earlier run produced, so it is always safe to retry.

Logs carry ids, counts and durations - never the text of the book.
"""

import asyncio
import logging
import time
import uuid

from sqlalchemy import delete, insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import DocumentStatus, FileKind, ProcessingStage
from app.models import Book, Chapter, Document, DocumentChunk, Exercise, Topic
from app.models.base import utcnow
from app.rag import embeddings
from app.rag.ingestion.chunking import ChunkDraft, make_chunks
from app.rag.ingestion.cleanup import remove_page_furniture
from app.rag.ingestion.errors import ProcessingError
from app.rag.ingestion.extract import extract_document
from app.rag.ingestion.labels import ChapterLike, ExerciseLike, TopicLike, build_context_label, embedding_text
from app.rag.ingestion.structure import DocumentStructure, StructureDetector
from app.rag.ingestion.text_quality import detect_language
from app.rag.ocr import get_ocr_provider, ocr_languages_for
from app.storage import get_file_storage

logger = logging.getLogger(__name__)


def _locate(
    found: list[tuple[ChapterLike, list[TopicLike], list[ExerciseLike]]], draft: ChunkDraft
) -> tuple[ChapterLike | None, TopicLike | None, ExerciseLike | None]:
    """The chapter, topic and exercise a chunk belongs to - from what was found or what was stored."""
    chapter, topics, exercises = found[draft.chapter] if draft.chapter is not None else (None, [], [])
    topic = topics[draft.topic] if draft.topic is not None else None
    exercise = exercises[draft.exercise] if draft.exercise is not None else None
    return chapter, topic, exercise


def _labels(book: Book, structure: DocumentStructure, drafts: list[ChunkDraft]) -> list[str]:
    found = [(chapter, chapter.topics, chapter.exercises) for chapter in structure.chapters]
    labels = []
    for draft in drafts:
        chapter, topic, exercise = _locate(found, draft)
        labels.append(
            build_context_label(
                class_level=book.class_level,
                subject=book.subject,
                chapter=chapter,
                topic=topic,
                exercise=exercise,
                content_type=draft.content_type,
                meta=draft.meta,
            )
        )
    return labels


async def _delete_outputs(db: AsyncSession, document_id: uuid.UUID) -> None:
    await db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document_id))
    await db.execute(delete(Chapter).where(Chapter.document_id == document_id))  # topics, exercises cascade


async def _set_stage(db: AsyncSession, document: Document, stage: ProcessingStage) -> None:
    document.stage = stage.value
    await db.commit()


async def _store(
    db: AsyncSession,
    document: Document,
    book: Book,
    structure: DocumentStructure,
    drafts: list[ChunkDraft],
    labels: list[str],
    vectors: list[list[float]],
    embedding_model: str,
) -> None:
    found: list[tuple[Chapter, list[Topic], list[Exercise]]] = []
    for position, detected in enumerate(structure.chapters):
        chapter = Chapter(
            id=uuid.uuid4(),
            book_id=book.id,
            document_id=document.id,
            number=detected.number,
            title=detected.title,
            position=position,
            page_start=detected.page_start,
            page_end=detected.page_end,
            detected_by=detected.detected_by,
        )
        topics = [
            Topic(chapter_id=chapter.id, number=t.number, title=t.title, position=i, page_start=t.page_start)
            for i, t in enumerate(detected.topics)
        ]
        exercises = [
            Exercise(
                chapter_id=chapter.id,
                label=e.label,
                position=i,
                page_start=e.page_start,
                page_end=e.page_end,
                question_count=e.question_count,
            )
            for i, e in enumerate(detected.exercises)
        ]
        db.add_all([chapter, *topics, *exercises])
        found.append((chapter, topics, exercises))
    await db.flush()

    now = utcnow()
    rows = []
    for position, (draft, label, vector) in enumerate(zip(drafts, labels, vectors, strict=True)):
        chapter, topic, exercise = _locate(found, draft)
        rows.append(
            {
                "id": uuid.uuid4(),
                "document_id": document.id,
                "owner_user_id": document.owner_user_id,
                "book_id": book.id,
                "chapter_id": chapter.id if chapter else None,
                "topic_id": topic.id if topic else None,
                "exercise_id": exercise.id if exercise else None,
                "content_type": draft.content_type.value,
                "content": draft.content,
                "context_label": label,
                "page_start": draft.page_start,
                "page_end": draft.page_end,
                "position": position,
                "token_count": draft.token_count,
                "class_level": book.class_level,
                "board": book.board,
                "subject": book.subject,
                "language": detect_language(draft.content, default=book.language),
                "meta": draft.meta,
                "embedding": vector,
                "embedding_model": embedding_model,
                "created_at": now,
                "updated_at": now,
            }
        )
    await db.execute(insert(DocumentChunk), rows)  # never empty: the caller fails documents without chunks


async def _fail(db: AsyncSession, document_id: uuid.UUID, code: str) -> None:
    await db.rollback()
    document = await db.get(Document, document_id, populate_existing=True)
    if document is None:
        return  # deleted while it was being read
    await _delete_outputs(db, document_id)
    document.status = DocumentStatus.FAILED.value
    document.error_code = code
    document.processing_finished_at = utcnow()
    await db.commit()


async def process_document(db: AsyncSession, *, document_id: uuid.UUID) -> None:
    """The background job. Safe to run again for the same document."""
    document = await db.get(Document, document_id)
    if document is None or document.status == DocumentStatus.READY:
        return
    book = await db.get(Book, document.book_id)
    if book is None:
        return

    started = time.perf_counter()
    await _delete_outputs(db, document.id)
    document.status = DocumentStatus.PROCESSING.value
    document.stage = ProcessingStage.EXTRACT_TEXT.value
    document.error_code = None
    document.attempts += 1
    document.processing_started_at = utcnow()
    document.processing_finished_at = None
    await db.commit()

    try:
        try:
            data = await get_file_storage().read_bytes(document.storage_key)
        except FileNotFoundError:
            raise ProcessingError("file_missing") from None

        ocr = get_ocr_provider()
        extracted = await extract_document(
            data, FileKind(document.file_kind), ocr=ocr, ocr_languages=ocr_languages_for(book.language)
        )
        del data
        remove_page_furniture(extracted.pages)
        pages_with_text = sum(1 for page in extracted.pages if page.lines)
        if pages_with_text == 0:
            scanned = extracted.unreadable_pages > 0 and ocr is None
            raise ProcessingError("scanned_document" if scanned else "no_text_found")

        await _set_stage(db, document, ProcessingStage.DETECT_CHAPTERS)
        detector = StructureDetector(
            extracted.pages, outline=extracted.outline, filename=document.original_filename
        )
        await asyncio.to_thread(detector.detect_chapters)

        await _set_stage(db, document, ProcessingStage.DETECT_EXERCISES)
        await asyncio.to_thread(detector.detect_exercises)

        await _set_stage(db, document, ProcessingStage.DETECT_TOPICS)
        structure = await asyncio.to_thread(detector.detect_topics)

        await _set_stage(db, document, ProcessingStage.MAKE_CHUNKS)
        drafts = await asyncio.to_thread(make_chunks, structure)
        if not drafts:
            raise ProcessingError("no_text_found")

        await _set_stage(db, document, ProcessingStage.EMBED_CHUNKS)
        labels = _labels(book, structure, drafts)
        embedder = embeddings.get_embedding_provider()
        vectors = await embedder.embed_passages(
            [embedding_text(label, draft.content) for label, draft in zip(labels, drafts, strict=True)]
        )
        await _store(db, document, book, structure, drafts, labels, vectors, embedder.model_name)

        document.status = DocumentStatus.READY.value
        document.stage = None
        document.page_count = document.page_count or extracted.page_count
        document.processing_finished_at = utcnow()
        document.stats = {
            "pages": extracted.page_count,
            "pages_with_text": pages_with_text,
            "ocr_pages": extracted.ocr_pages,
            "unreadable_pages": extracted.unreadable_pages,
            "chapters": len(structure.chapters),
            "topics": structure.topic_count,
            "exercises": structure.exercise_count,
            "questions": structure.question_count,
            "examples": structure.example_count,
            "chunks": len(drafts),
        }
        await db.commit()
        logger.info(
            "Document %s ready in %.1f s: %s",
            document_id,
            time.perf_counter() - started,
            ", ".join(f"{key}={value}" for key, value in document.stats.items()),
        )
    except ProcessingError as exc:
        logger.info("Document %s could not be read: %s", document_id, exc.code)
        await _fail(db, document_id, exc.code)
    except asyncio.CancelledError:
        raise  # the server is stopping; the document is picked up again at the next start
    except Exception:
        logger.exception("Document %s failed while reading", document_id)
        await _fail(db, document_id, "processing_failed")
