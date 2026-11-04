"""Previous-year paper analysis: where the marks go, and a test like the papers."""

import uuid
from typing import Literal

from pydantic import BaseModel, Field

from app.analytics.paper_reading import PaperFormat
from app.analytics.papers import Trend
from app.schemas.adaptive import Area
from app.schemas.library import DocumentError
from app.schemas.mock_test import MockTestCreate
from app.schemas.practice import PracticeCreate


class PaperOut(BaseModel):
    """One paper (one file of the book)."""

    document_id: uuid.UUID
    title: str = Field(description="Named after its file.")
    status: Literal["new", "preparing", "ready", "failed"] = Field(
        description="new: added since the last analysis."
    )
    error: DocumentError | None
    year: int | None
    duration_minutes: int | None
    negative_marks: float = Field(description="Marks lost for a wrong objective answer; 0: none.")
    questions: int
    total_marks: float = Field(description="A question whose marks are not shown counts as 1.")


class YearMarks(BaseModel):
    year: int
    marks: float


class ChapterMarks(Area):
    """A chapter of the textbooks (`topic` is always null) and what the papers ask from it."""

    questions: int
    marks_per_paper: float = Field(description="Its marks, averaged over the analysed papers.")
    share: float = Field(description="Its share of all the papers' marks, 0-1.")
    papers: int = Field(description="How many of the papers ask from it.")
    trend: Trend | None = Field(description="Over the papers that show their year (3 or more).")
    by_year: list[YearMarks] = Field(description="Its marks in each paper that shows its year.")
    practice: PracticeCreate = Field(description="Create Practice for it (add `student_id`).")


class TopicAsked(Area):
    questions: int
    papers: int


class FormatShare(BaseModel):
    format: PaperFormat
    questions: int
    marks: float
    share: float = Field(description="Of the questions, 0-1.")


class LayoutSection(BaseModel):
    title: str = Field(description='As printed, e.g. "Section A".')
    questions: int
    marks: int = Field(description="Marks for each question.")
    formats: list[PaperFormat] = Field(description="Most frequent first.")


class Unmatched(BaseModel):
    questions: int
    marks: float


class PaperAnalysisOut(BaseModel):
    book_id: uuid.UUID
    status: Literal["none", "preparing", "ready", "failed"] = Field(
        description="none: never analysed. `preparing` while the papers are read - poll until it changes."
    )
    papers: list[PaperOut] = Field(description="Every paper read so far, the latest first.")
    chapters: list[ChapterMarks] = Field(description="Most marks first.")
    unmatched: Unmatched = Field(description="Questions no chapter of the textbooks teaches.")
    topics: list[TopicAsked] = Field(description="The topics asked most (in the most papers).")
    formats: list[FormatShare]
    layout: list[LayoutSection] = Field(description="The sections of the latest paper.")
    layout_year: int | None
    test: MockTestCreate | None = Field(
        description="A test like the papers (add `student_id`); null until a question matches a chapter."
    )
