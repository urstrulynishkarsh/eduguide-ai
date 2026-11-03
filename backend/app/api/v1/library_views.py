"""Turning library rows into API responses (progress checklist, book status, sources)."""

from app.core.enums import ClassLevel, DocumentStatus, ProcessingStage
from app.models import Book, Chapter, Document, DocumentChunk, Exercise, Topic
from app.rag.ingestion.errors import processing_error_message
from app.rag.ingestion.labels import chapter_label
from app.schemas.library import (
    BookOut,
    BookStatus,
    ChapterDetail,
    ChapterOut,
    DocumentError,
    DocumentOut,
    DocumentSummary,
    ExerciseDetail,
    ExerciseOut,
    ProgressState,
    ProgressStep,
    Source,
    TextbookQuestion,
    TopicOut,
)

_STAGES = list(ProcessingStage)


def progress(document: Document) -> list[ProgressStep]:
    status = DocumentStatus(document.status)
    current = _STAGES.index(ProcessingStage(document.stage)) if document.stage else None
    steps = []
    for position, stage in enumerate(_STAGES):
        state: ProgressState = "pending"
        if status is DocumentStatus.READY:
            state = "done"
        elif current is not None and status in (DocumentStatus.PROCESSING, DocumentStatus.FAILED):
            if position < current:
                state = "done"
            elif position == current:
                state = "active" if status is DocumentStatus.PROCESSING else "failed"
        steps.append(ProgressStep(step=stage, state=state))
    return steps


def document_out(document: Document) -> DocumentOut:
    error = None
    if document.status == DocumentStatus.FAILED and document.error_code:
        error = DocumentError(code=document.error_code, message=processing_error_message(document.error_code))
    return DocumentOut(
        id=document.id,
        book_id=document.book_id,
        original_filename=document.original_filename,
        file_type=document.file_kind,
        size_bytes=document.size_bytes,
        page_count=document.page_count,
        status=document.status,
        stage=document.stage,
        progress=progress(document),
        error=error,
        summary=DocumentSummary(**document.stats),
        created_at=document.created_at,
        updated_at=document.updated_at,
        processing_finished_at=document.processing_finished_at,
    )


def book_status(book: Book) -> BookStatus:
    statuses = {document.status for document in book.documents}
    if not statuses:
        return "empty"
    if statuses & {DocumentStatus.QUEUED.value, DocumentStatus.PROCESSING.value}:
        return "processing"
    if statuses == {DocumentStatus.FAILED.value}:
        return "failed"
    return "ready"


def book_out(book: Book, chapter_count: int) -> BookOut:
    return BookOut(
        id=book.id,
        title=book.title,
        subject=book.subject,
        material_type=book.material_type,
        class_level=book.class_level,
        class_label=ClassLevel(book.class_level).label,
        board=book.board,
        language=book.language,
        student_id=book.student_id,
        status=book_status(book),
        chapter_count=chapter_count,
        documents=[document_out(document) for document in book.documents],
        created_at=book.created_at,
        updated_at=book.updated_at,
    )


def chapter_out(chapter: Chapter, counts: dict[str, int]) -> ChapterOut:
    return ChapterOut(
        id=chapter.id,
        book_id=chapter.book_id,
        document_id=chapter.document_id,
        number=chapter.number,
        title=chapter.title,
        label=chapter_label(chapter.number, chapter.title),
        page_start=chapter.page_start,
        page_end=chapter.page_end,
        detected_by=chapter.detected_by,
        topic_count=counts["topics"],
        exercise_count=counts["exercises"],
        question_count=counts["questions"],
    )


def exercise_title(label: str) -> str:
    return f"Exercise {label}" if label else "Exercises"


def exercise_out(exercise: Exercise) -> ExerciseOut:
    return ExerciseOut(
        id=exercise.id,
        label=exercise.label,
        title=exercise_title(exercise.label),
        page_start=exercise.page_start,
        page_end=exercise.page_end,
        question_count=exercise.question_count,
    )


def chapter_detail(
    chapter: Chapter, counts: dict[str, int], topics: list[Topic], exercises: list[Exercise]
) -> ChapterDetail:
    return ChapterDetail(
        **chapter_out(chapter, counts).model_dump(),
        topics=[TopicOut.model_validate(topic) for topic in topics],
        exercises=[exercise_out(exercise) for exercise in exercises],
        example_count=counts["examples"],
        has_summary=counts["summaries"] > 0,
    )


def exercise_detail(
    exercise: Exercise, chapter: Chapter, book: Book, questions: list[DocumentChunk]
) -> ExerciseDetail:
    chapter_name = chapter_label(chapter.number, chapter.title)
    return ExerciseDetail(
        **exercise_out(exercise).model_dump(),
        chapter_id=chapter.id,
        book_id=book.id,
        questions=[
            TextbookQuestion(
                id=chunk.id,
                number=chunk.meta.get("question_number"),
                text=chunk.content,
                instructions=chunk.meta.get("instructions"),
                page_start=chunk.page_start,
                page_end=chunk.page_end,
                source=Source(
                    book_id=book.id,
                    book_title=book.title,
                    chapter=chapter_name,
                    exercise=exercise.label or None,
                    page=chunk.page_start,
                ),
            )
            for chunk in questions
        ],
    )
