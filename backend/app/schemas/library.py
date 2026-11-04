"""My Books: request and response shapes for books, documents, chapters and exercises."""

import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.core.enums import Board, ClassLevel, DocumentStatus, FileKind, MaterialType, ProcessingStage
from app.core.languages import is_medium

BookTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
SubjectName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
ChapterTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]


def _check_book_language(value: str | None) -> str | None:
    # A book can be in any medium language (Marathi, Tamil...), even before the AI can write it.
    if value is not None and (value == "other" or not is_medium(value)):
        raise ValueError("Unknown language.")
    return value


class BookCreate(BaseModel):
    """Class, board and language may be left out when `student_id` is given: they are taken from
    that child's profile. A student who signed up alone gets their own profile automatically."""

    title: BookTitle
    subject: SubjectName
    material_type: MaterialType = MaterialType.TEXTBOOK
    student_id: uuid.UUID | None = Field(default=None, description="The child this book is for (optional).")
    class_level: ClassLevel | None = None
    board: Board | None = None
    language: str | None = Field(
        default=None, description="Language the book is written in, e.g. `en`, `hi`."
    )

    _language = field_validator("language")(_check_book_language)


class BookUpdate(BaseModel):
    """Only the fields that are sent are changed."""

    title: BookTitle | None = None
    subject: SubjectName | None = None
    material_type: MaterialType | None = None
    student_id: uuid.UUID | None = None
    class_level: ClassLevel | None = None
    board: Board | None = None
    language: str | None = None

    _language = field_validator("language")(_check_book_language)

    @field_validator("title", "subject", "material_type", "class_level", "board", "language")
    @classmethod
    def _cannot_be_cleared(cls, value: object) -> object:
        if value is None:
            raise ValueError("This field cannot be empty.")
        return value


ProgressState = Literal["pending", "active", "done", "failed"]


class ProgressStep(BaseModel):
    """One row of the upload checklist. The frontend shows it in parent words
    (e.g. `detect_chapters` -> "Finding the chapters")."""

    step: ProcessingStage
    state: ProgressState


class DocumentError(BaseModel):
    code: str
    message: str


class DocumentSummary(BaseModel):
    """What was found in the document. Empty until it is ready."""

    pages: int | None = None
    pages_with_text: int | None = None
    ocr_pages: int | None = Field(default=None, description="Scanned pages that were read with OCR.")
    unreadable_pages: int | None = Field(default=None, description="Pages that could not be read.")
    chapters: int | None = None
    topics: int | None = None
    exercises: int | None = None
    questions: int | None = None
    examples: int | None = None
    chunks: int | None = None


class DocumentOut(BaseModel):
    id: uuid.UUID
    book_id: uuid.UUID
    original_filename: str
    file_type: FileKind
    size_bytes: int
    page_count: int | None
    status: DocumentStatus
    stage: ProcessingStage | None = Field(description="The step running now, or the one that failed.")
    progress: list[ProgressStep]
    error: DocumentError | None
    summary: DocumentSummary
    created_at: datetime
    updated_at: datetime
    processing_finished_at: datetime | None


BookStatus = Literal["empty", "processing", "ready", "failed"]


class BookOut(BaseModel):
    id: uuid.UUID
    title: str
    subject: str
    material_type: MaterialType
    class_level: ClassLevel
    class_label: str
    board: Board
    language: str
    student_id: uuid.UUID | None
    status: BookStatus = Field(
        description="`empty`: no files yet · `processing`: a file is being read · `ready`: at least one "
        "file is ready and none is being read · `failed`: every file failed."
    )
    chapter_count: int
    documents: list[DocumentOut]
    created_at: datetime
    updated_at: datetime


class BookPage(BaseModel):
    items: list[BookOut]
    next_cursor: str | None = Field(
        description="Pass as `cursor` to get the next page; null on the last page."
    )


class ChapterOut(BaseModel):
    id: uuid.UUID
    book_id: uuid.UUID
    document_id: uuid.UUID
    number: int | None
    title: str
    label: str = Field(description='Display name, e.g. "Chapter 2 Linear Equations".')
    page_start: int | None
    page_end: int | None
    detected_by: str
    topic_count: int
    exercise_count: int
    question_count: int


class ChapterUpdate(BaseModel):
    """A parent corrects what was found: rename a chapter or fix its number (null = no number)."""

    title: ChapterTitle | None = None
    number: Annotated[int, Field(ge=0, le=999)] | None = None

    @field_validator("title")
    @classmethod
    def _title_cannot_be_cleared(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("A title is required.")
        return value


class TopicOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    number: str | None
    title: str
    page_start: int | None


class ExerciseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    label: str
    title: str = Field(
        description='"Exercise 2.3", "Exercises" when the book gives no number, a paper\'s "Section A".'
    )
    page_start: int | None
    page_end: int | None
    question_count: int


class ChapterDetail(ChapterOut):
    topics: list[TopicOut]
    exercises: list[ExerciseOut]
    example_count: int
    has_summary: bool


class Source(BaseModel):
    """Where something came from (spec §42): shown as "Based on: Class 8 Mathematics, Chapter ..."."""

    book_id: uuid.UUID
    book_title: str
    chapter: str | None
    exercise: str | None = None
    page: int | None = None


class TextbookQuestion(BaseModel):
    """A question exactly as printed in the uploaded book. Always `origin: "textbook"` -
    generated questions (Step 4) are marked `"generated"`."""

    id: uuid.UUID
    number: str | None
    text: str
    instructions: str | None = Field(
        description='Text before question 1, e.g. "Solve the following equations."'
    )
    page_start: int | None
    page_end: int | None
    origin: Literal["textbook"] = "textbook"
    source: Source


class ExerciseDetail(ExerciseOut):
    chapter_id: uuid.UUID
    book_id: uuid.UUID
    questions: list[TextbookQuestion]
