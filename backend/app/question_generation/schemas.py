"""Shapes the AI fills in. Every answer is parsed into these and checked before it is stored."""

from typing import Literal

from pydantic import BaseModel, Field

from app.core.enums import QuestionFormat, QuestionStyle

Difficulty = Literal["easy", "medium", "hard"]

# How each format is answered and checked.
CHOICE_FORMATS = frozenset(
    {
        QuestionFormat.MCQ,
        QuestionFormat.VISUAL_CHOICE,
        QuestionFormat.TRUE_FALSE,
        QuestionFormat.ASSERTION_REASON,
        QuestionFormat.CASE_BASED,
    }
)
NUMBER_FORMATS = frozenset({QuestionFormat.NUMERICAL, QuestionFormat.COUNTING})
WRITTEN_FORMATS = frozenset({QuestionFormat.SHORT_ANSWER, QuestionFormat.LONG_ANSWER})


class GeneratedQuestion(BaseModel):
    format: QuestionFormat
    style: QuestionStyle
    difficulty: Difficulty
    case: str | None = Field(description="case_based only: the short case the question is about.")
    text: str = Field(description="The question. fill_blank: mark the blank with ____.")
    options: list[str] = Field(description="Choice formats only; empty otherwise.")
    correct_option: int | None = Field(description="Choice formats: 0-based index of the correct option.")
    numeric_answer: float | None = Field(description="numerical and counting.")
    unit: str | None
    accepted_answers: list[str] = Field(description="fill_blank: every acceptable answer.")
    match_left: list[str]
    match_right: list[str] = Field(description="matching: match_right[i] is the match for match_left[i].")
    model_answer: str | None = Field(description="short_answer and long_answer.")
    key_points: list[str] = Field(description="Written formats: what a correct answer must contain.")
    hints: list[str] = Field(description="From a gentle nudge to the method; never the answer.")
    concept: str = Field(description="The idea the question practises, in one or two sentences.")
    steps: list[str] = Field(description="The worked solution, step by step.")
    final_answer: str
    source_tags: list[str] = Field(description='Tags of the passages the question is built on, e.g. ["S2"].')


class GeneratedBatch(BaseModel):
    questions: list[GeneratedQuestion]


class Review(BaseModel):
    """An independent check of one question by a second call that does not see choice/number answers."""

    number: int
    solved_option: int | None = Field(description="Choice formats: the option you get, 0-based.")
    solved_value: float | None = Field(description="numerical and counting: the number you get.")
    solved_text: str | None = Field(description="fill_blank: the word or phrase you get.")
    shown_answer_correct: bool | None = Field(description="matching and written formats only.")
    supported_by_passages: bool
    fits_class: bool = Field(description="No ideas beyond this class; wording suits the age.")
    difficulty: Difficulty
    problem: str = Field(description="One sentence if something is wrong; empty otherwise.")


class ReviewBatch(BaseModel):
    reviews: list[Review]


class Grade(BaseModel):
    """Marking of a written answer."""

    is_correct: bool
    feedback: str = Field(description="One or two kind sentences: what was right and what to add.")
