"""Practice: Create Practice (spec §18), doing it, help (§20), explain (§21) and progress."""

import uuid
from datetime import datetime
from typing import Annotated, Literal, Self

from pydantic import BaseModel, Field, StringConstraints, field_validator, model_validator

from app.core.enums import QuestionFormat, QuestionStyle
from app.core.languages import is_content_language
from app.models import Question
from app.rag.answering import ExplainStyle
from app.schemas.library import DocumentError, Source
from app.schemas.rewards import RewardGain

SessionDifficulty = Literal["easy", "medium", "hard", "mixed"]
SessionStatus = Literal["preparing", "ready", "completed", "failed"]
HelpLevel = Literal["hint", "steps", "answer"]


class QuestionRequest(BaseModel):
    """Which questions, for practice or a test. Leave book, chapter, topic and exercise empty to use
    all of the learner's books."""

    student_id: uuid.UUID | None = Field(default=None, description="Which child (parents only).")
    book_id: uuid.UUID | None = None
    chapter_id: uuid.UUID | None = None
    topic_id: uuid.UUID | None = Field(
        default=None, description='One topic, e.g. "4.3 Equations in Daily Life".'
    )
    exercise_id: uuid.UUID | None = None
    count: Annotated[int, Field(ge=1, le=50)] | None = Field(
        default=None, description="Number of questions; the class's usual number when left out."
    )
    difficulty: SessionDifficulty = "mixed"
    language: str | None = Field(
        default=None, description="en, hi or hinglish; the learner's language if empty."
    )

    @field_validator("language")
    @classmethod
    def _language_must_be_supported(cls, value: str | None) -> str | None:
        if value is not None and not is_content_language(value):
            raise ValueError("This language is not available yet.")
        return value

    @model_validator(mode="after")
    def _one_place_at_most(self) -> Self:
        places = (self.book_id, self.chapter_id, self.topic_id, self.exercise_id)
        if sum(place is not None for place in places) > 1:
            raise ValueError("Choose a book, a chapter, a topic or an exercise - not more than one.")
        return self


class PracticeCreate(QuestionRequest):
    question_type: QuestionFormat | Literal["mixed"] = Field(
        default="mixed", description='"mixed", or one format the class allows (e.g. "mcq", "numerical").'
    )


class QuestionView(BaseModel):
    """A question as the learner sees it - never with its answer."""

    id: uuid.UUID
    number: int
    format: QuestionFormat
    style: QuestionStyle
    difficulty: str
    case: str | None
    text: str
    options: list[str]
    match_left: list[str]
    match_right: list[str]
    unit: str | None
    origin: Literal["generated"] = Field(
        default="generated", description="Written by the AI from the book - not the book's own question."
    )
    source: Source = Field(description='Shown as "Generated from concepts in: …".')

    @classmethod
    def of(cls, question: Question, number: int, source: Source) -> "QuestionView":
        body = question.body
        return cls(
            id=question.id,
            number=number,
            format=question.format,
            style=question.style,
            difficulty=question.difficulty,
            case=body.get("case"),
            text=body["text"],
            options=body.get("options", []),
            match_left=body.get("left", []),
            match_right=body.get("right", []),
            unit=body.get("unit"),
            source=source,
        )


class ItemView(BaseModel):
    question: QuestionView
    attempts: int
    correct: bool | None = Field(description="Result of the latest answer; null before the first one.")
    hints_shown: int
    hints_total: int
    steps_shown: bool
    answer_shown: bool


class SessionOut(BaseModel):
    id: uuid.UUID
    student_id: uuid.UUID
    status: SessionStatus = Field(description="`preparing` while questions are written - poll until `ready`.")
    error: DocumentError | None
    question_count: int = Field(description="How many were asked for; `items` can hold fewer.")
    difficulty: SessionDifficulty
    question_type: str
    language: str
    items: list[ItemView]
    answered: int
    correct: int
    created_at: datetime
    completed_at: datetime | None


class Response(BaseModel):
    """Fill the field that fits the question: `option` (choice formats), `value` (numerical,
    counting), `text` (fill_blank, short_answer, long_answer) or `pairs` (matching: for each
    left item, the index of its right item)."""

    option: int | None = None
    value: float | None = None
    text: Annotated[str, StringConstraints(strip_whitespace=True, max_length=5000)] | None = None
    pairs: list[int] | None = Field(default=None, max_length=5)
    time_taken_ms: Annotated[int, Field(ge=0, le=3_600_000)] | None = None


class AnswerIn(Response):
    question_id: uuid.UUID


class AnswerResult(BaseModel):
    correct: bool
    try_again: bool = Field(description="Nursery-Class 2: wrong answers are an invitation to try again.")
    feedback: str | None = Field(description="Feedback on written answers.")
    correct_answer: str | None = Field(description="Shown once the answer is final.")
    session_completed: bool
    rewards: RewardGain = Field(description="The XP and badges this answer earned (trying again earns none).")


class HelpIn(BaseModel):
    level: HelpLevel = Field(description="[Hint] · [Show Steps] · [Show Answer]")


class HelpOut(BaseModel):
    level: HelpLevel
    hint: str | None
    hints_left: int
    concept: str | None
    steps: list[str]
    final_answer: str | None


class ExplainQuestionIn(BaseModel):
    style: ExplainStyle = "normal"


class AreaProgress(BaseModel):
    id: uuid.UUID
    name: str
    attempted: int
    accuracy: float


class SessionSummary(BaseModel):
    id: uuid.UUID
    status: SessionStatus
    questions: int
    answered: int
    correct: int
    created_at: datetime


class ProgressOut(BaseModel):
    """Basic performance. Accuracy counts the first answer to each question in a session."""

    student_id: uuid.UUID
    questions_answered: int
    correct_first_time: int
    accuracy: float | None
    time_spent_ms: int
    hints_used: int
    sessions_completed: int
    by_chapter: list[AreaProgress]
    by_topic: list[AreaProgress]
    recent_sessions: list[SessionSummary]
