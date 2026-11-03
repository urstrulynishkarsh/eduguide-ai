"""The parent dashboard in one call (docs/04 §4.3): the week, what the child knows, what to do next,
recent tests and today's plan. The Parent AI Assistant reads the same snapshot."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.question_generation.paper import TestKind
from app.schemas.adaptive import AreaMastery, RecommendationOut
from app.schemas.study_plan import PlanItemOut


class DayProgress(BaseModel):
    day: date = Field(description="India time.")
    answered: int = Field(description="Questions answered (the first answer to each).")
    correct: int = Field(description="Of those, right the first time.")
    minutes: int


class TestResult(BaseModel):
    attempt_id: uuid.UUID
    mock_test_id: uuid.UUID
    kind: TestKind
    place: str | None = Field(description="The test's topic, chapter or book; null: all books.")
    score: float
    total_marks: int
    percentage: float
    submitted_at: datetime


class PlanToday(BaseModel):
    plan_id: uuid.UUID
    exam_date: date
    days_left: int
    done: int
    total: int
    today: list[PlanItemOut] = Field(description="Today's tasks of the study plan.")


class DashboardOut(BaseModel):
    student_id: uuid.UUID
    week: list[DayProgress] = Field(description="The last 7 days, oldest first.")
    strong: list[AreaMastery] = Field(description="Up to 3 strong areas, strongest first.")
    needs_attention: list[AreaMastery] = Field(
        description="Up to 3 areas that need attention, weakest first."
    )
    recommendations: list[RecommendationOut] = Field(
        description="Today's Recommended for You; the first is the one to start with."
    )
    tests: list[TestResult] = Field(description="The last 3 tests submitted, newest first.")
    plan: PlanToday | None = Field(description="Today in the study plan; null without a plan.")
