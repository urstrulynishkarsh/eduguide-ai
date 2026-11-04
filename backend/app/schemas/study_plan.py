"""The study planner: a plan from today to an exam, as daily tasks that follow performance."""

import uuid
from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.schemas.adaptive import Reason
from app.schemas.learn import ExplainRequest
from app.schemas.mock_test import MockTestCreate
from app.schemas.practice import PracticeCreate

ItemStatus = Literal["pending", "done", "skipped", "missed"]


class StudyPlanCreate(BaseModel):
    """A learner has one plan; a new one replaces it."""

    student_id: uuid.UUID | None = Field(default=None, description="Which child (parents only).")
    exam_date: date = Field(description="After today (India time), at most a year ahead.")
    daily_minutes: Annotated[int, Field(ge=10, le=300)] = 30
    target_score: Annotated[int, Field(ge=40, le=100)] = Field(
        default=80, description="The percent to aim for: chapters below it get more practice."
    )
    chapter_ids: list[uuid.UUID] = Field(
        default_factory=list,
        max_length=200,
        description="The chapters the exam covers; empty = every chapter of the learner's books for "
        "their class.",
    )


class PlanItemOut(BaseModel):
    id: uuid.UUID
    day: date
    kind: Literal["learn", "practice", "test"]
    status: ItemStatus = Field(description="`missed`: a day passed with the task still pending.")
    minutes: int
    difficulty: str
    reason: Reason
    book_id: uuid.UUID
    book_title: str
    chapter_id: uuid.UUID | None = Field(description="Null for a test of the whole book.")
    chapter: str | None
    topic_id: uuid.UUID | None
    topic: str | None
    practice: PracticeCreate | None = Field(description="practice: send as-is to POST /practice/sessions.")
    revise: ExplainRequest | None = Field(description="learn: send as-is to POST /learn/explain.")
    test: MockTestCreate | None = Field(description="test: send as-is to POST /mock-tests.")


class PlanDay(BaseModel):
    day: date
    minutes: int
    items: list[PlanItemOut]


class StudyPlanOut(BaseModel):
    id: uuid.UUID
    student_id: uuid.UUID
    exam_date: date
    daily_minutes: int
    target_score: int
    chapter_ids: list[uuid.UUID]
    status: Literal["active", "finished"] = Field(description="finished once the exam day has come.")
    days_left: int
    planned_on: date = Field(
        description="The remaining days are planned again on the first visit of each day."
    )
    unscheduled: int = Field(
        description="Tasks that did not fit before the exam: add minutes or drop chapters."
    )
    done: int
    missed: int
    total: int
    days: list[PlanDay]


class PlanItemUpdate(BaseModel):
    status: Literal["pending", "done", "skipped"]
