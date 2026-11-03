"""Adaptive learning: what the learner knows (spec §23) and Recommended for You (spec §11-12)."""

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.learn import ExplainRequest
from app.schemas.practice import PracticeCreate

Level = Literal["easy", "medium", "hard"]
MasteryStatus = Literal["needs_attention", "learning", "strong"]
RecommendationKind = Literal["strengthen", "continue", "review", "new_chapter"]


class Area(BaseModel):
    """A topic of a chapter - or the chapter itself, for questions that have no topic."""

    book_id: uuid.UUID
    book_title: str
    chapter_id: uuid.UUID
    chapter: str = Field(description='e.g. "Chapter 4 Simple Equations".')
    topic_id: uuid.UUID | None
    topic: str | None = Field(description='e.g. "4.3 Equations in Daily Life"; null: the chapter in general.')


class AreaMastery(Area):
    status: MasteryStatus = Field(
        description="needs_attention: below 60% right over at least 5 answers (Class 6-12 only); "
        "strong: mastery of 0.85 or more over at least 5 answers; otherwise learning."
    )
    mastery: float = Field(
        description="0-1. Recent answers and harder questions count more; a right answer after hints "
        "or the solution counts less."
    )
    confidence: float = Field(description="0-1: how much evidence there is (10 answers = 1).")
    accuracy: float = Field(description="Share right in the last 10 answers.")
    attempts: int
    avg_time_ms: int | None
    difficulty: Level | None = Field(
        description="The level for the next practice here, following performance. "
        "Null where the class has no adaptive difficulty (Nursery - Class 5)."
    )
    last_practised_at: datetime


class MasteryOut(BaseModel):
    student_id: uuid.UUID
    areas: list[AreaMastery] = Field(description="Every area practised, weakest first.")


class RecommendationOut(Area):
    id: uuid.UUID
    kind: RecommendationKind = Field(
        description="strengthen (a weak area) · continue (being learned) · review (not practised for a "
        "week) · new_chapter (never practised)"
    )
    status: Literal["active", "done"] = Field(description="done once a practice of this place is finished.")
    reason: str
    practice: PracticeCreate = Field(
        description="Start Recommended Practice: send as-is to POST /practice/sessions."
    )
    revise: ExplainRequest | None = Field(
        description="strengthen only: a concept revision first, sent as-is to POST /learn/explain."
    )


class RecommendationsOut(BaseModel):
    student_id: uuid.UUID
    day: date = Field(description="Today in India time; a new list is made each day.")
    items: list[RecommendationOut] = Field(description="At most three, in the order to do them.")
