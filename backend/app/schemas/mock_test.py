"""Mock tests: a paper in sections, taking it, and its result report."""

import uuid
from datetime import datetime
from typing import Annotated, Literal, Self

from pydantic import BaseModel, Field, model_validator

from app.question_generation.paper import TestKind
from app.schemas.adaptive import Area
from app.schemas.library import DocumentError
from app.schemas.practice import QuestionRequest, QuestionView, Response, SessionDifficulty


class MockTestCreate(QuestionRequest):
    """`practice` (Class 3+): a short test of any one place, or of all books. `chapter` (Class 6+):
    one chapter. `full_mock` (Class 9+): a whole book, or all books - always timed. `previous_year`
    (Class 9+): `book_id` is a book of previous-year papers, analysed; the test follows its pattern and
    the chapters of the textbooks that carry the most marks - always timed. A Class 11-12 learner whose
    goal is JEE, NEET or CUET gets the other kinds in that exam's pattern."""

    kind: TestKind = "practice"
    duration_minutes: Annotated[int, Field(ge=5, le=240)] | None = Field(
        default=None,
        description="A time limit (Class 9-12 only). A full mock test without one gets about 2 minutes "
        "a mark.",
    )

    @model_validator(mode="after")
    def _place_fits_the_kind(self) -> Self:
        if self.kind == "chapter" and self.chapter_id is None:
            raise ValueError("A chapter test needs a chapter.")
        if self.kind == "full_mock" and (self.chapter_id or self.topic_id or self.exercise_id):
            raise ValueError("A full mock test covers a whole book, or all books.")
        if self.kind == "previous_year" and self.book_id is None:
            raise ValueError("A previous-year pattern test needs the book of previous-year papers.")
        return self


class PaperSection(BaseModel):
    code: str = Field(description='"A", "B", ...')
    title: str = Field(description='e.g. "Objective questions".')
    marks: int = Field(description="Marks for each question of the section.")
    negative: float = Field(description="Marks lost for each wrong answer; 0: no negative marking.")
    questions: list[QuestionView]


Exam = Literal["jee", "neet", "cuet"]


class AttemptSummary(BaseModel):
    id: uuid.UUID
    started_at: datetime
    submitted_at: datetime | None
    score: float | None


class MockTestSummary(BaseModel):
    """The place is the most specific of book, chapter, topic and exercise (all empty = all books)."""

    id: uuid.UUID
    student_id: uuid.UUID
    kind: TestKind
    exam: Exam | None = Field(
        description="The competitive exam whose pattern it follows; null: a school paper."
    )
    status: Literal["preparing", "ready", "failed"] = Field(
        description="`preparing` while questions are written - poll until `ready`."
    )
    book_id: uuid.UUID | None
    book_title: str | None
    chapter_id: uuid.UUID | None
    chapter: str | None
    topic_id: uuid.UUID | None
    topic: str | None
    exercise_id: uuid.UUID | None
    exercise: str | None
    question_count: int = Field(description="How many were asked for; the paper can hold fewer.")
    total_marks: int
    duration_minutes: int | None = Field(description="Null: untimed.")
    difficulty: SessionDifficulty
    language: str
    attempts: list[AttemptSummary] = Field(description="Every sitting, the latest last.")
    created_at: datetime


class MockTestOut(MockTestSummary):
    error: DocumentError | None
    sections: list[PaperSection] = Field(description="The questions, never with their answers.")


class MockTestPage(BaseModel):
    items: list[MockTestSummary]
    next_cursor: str | None = Field(
        description="Pass as `cursor` to get the next page; null on the last page."
    )


class AttemptOut(BaseModel):
    id: uuid.UUID
    mock_test_id: uuid.UUID
    status: Literal["in_progress", "submitted"]
    started_at: datetime
    deadline: datetime | None = Field(description="Null: untimed. Answers are not saved after it.")
    seconds_left: int | None
    submitted_at: datetime | None
    total_marks: int
    sections: list[PaperSection]
    responses: dict[uuid.UUID, Response] = Field(description="The answers saved so far, by question id.")


class Solution(BaseModel):
    concept: str
    steps: list[str]
    final_answer: str


class ReportQuestion(BaseModel):
    question: QuestionView
    section: str
    marks: int
    marks_awarded: float | None = Field(
        description="Null: not answered. Written answers can earn part marks; a wrong answer in a paper "
        "with negative marking loses marks (below 0)."
    )
    correct: bool | None
    response: Response | None
    feedback: str | None = Field(description="Feedback on written answers.")
    solution: Solution


class SectionResult(BaseModel):
    code: str
    title: str
    score: float
    total_marks: int
    answered: int
    correct: int


class AreaResult(Area):
    questions: int
    correct: int
    accuracy: float


class TestReport(BaseModel):
    attempt_id: uuid.UUID
    mock_test_id: uuid.UUID
    kind: TestKind
    score: float
    total_marks: int
    percentage: float
    time_taken_ms: int
    submitted_at: datetime
    answered: int
    correct: int
    wrong: int
    unanswered: int
    sections: list[SectionResult]
    areas: list[AreaResult] = Field(description="Chapters and topics of the paper, weakest first.")
    questions: list[ReportQuestion]
