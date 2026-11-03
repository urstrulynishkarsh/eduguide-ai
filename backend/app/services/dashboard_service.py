"""The parent dashboard in one call: a snapshot of one learner, for whoever may see them.

The Parent AI Assistant reads the same snapshot (services/chat_service.py), so what it says always
matches the screen. Reading it can make today's recommendations and re-plan the study plan, as
their own endpoints do on the first visit of a day.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.adaptive_learning import mastery, recommendations
from app.analytics import progress
from app.auth.principal import Principal
from app.models import Student
from app.schemas.dashboard import DashboardOut, PlanToday
from app.services import library_service, mock_test_service, student_service, study_plan_service

SHOWN = 3  # strong areas, areas that need attention, and tests


async def snapshot(db: AsyncSession, student: Student) -> DashboardOut:
    today = recommendations.today()
    owner = await student_service.account_of(db, student)
    areas = (await mastery.knowledge_profile(db, student)).areas  # weakest first
    plan = await study_plan_service.current_plan(db, student)
    todays = next((day.items for day in plan.days if day.day == today), []) if plan else []
    return DashboardOut(
        student_id=student.id,
        week=await progress.week(db, student.id, today),
        strong=[area for area in reversed(areas) if area.status == "strong"][:SHOWN],
        needs_attention=[area for area in areas if area.status == "needs_attention"][:SHOWN],
        recommendations=(
            await recommendations.for_today(db, student, library_service.books_for_learner(owner, student.id))
        ).items,
        tests=await mock_test_service.recent_results(db, student.id, SHOWN),
        plan=PlanToday(
            plan_id=plan.id,
            exam_date=plan.exam_date,
            days_left=plan.days_left,
            done=plan.done,
            total=plan.total,
            today=todays,
        )
        if plan
        else None,
    )


async def dashboard(db: AsyncSession, principal: Principal, student_id: uuid.UUID) -> DashboardOut:
    student = student_service.require_profile(await student_service.get_student(db, principal, student_id))
    return await snapshot(db, student)
