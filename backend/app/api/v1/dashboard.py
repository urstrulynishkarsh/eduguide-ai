"""The parent dashboard in one call, and progress over time."""

import uuid

from fastapi import APIRouter

from app.api.deps import CurrentPrincipal, DbSession
from app.schemas.dashboard import DashboardOut, TrendsOut
from app.services import dashboard_service

router = APIRouter(tags=["Dashboard"])


@router.get("/students/{student_id}/dashboard", response_model=DashboardOut, summary="Dashboard")
async def student_dashboard(
    student_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession
) -> DashboardOut:
    """This week day by day, strong areas and those that need attention, today's Recommended for You
    (with Start Recommended Practice), the last tests and today's study plan."""
    return await dashboard_service.dashboard(db, principal, student_id)


@router.get("/students/{student_id}/progress/trends", response_model=TrendsOut, summary="Progress over time")
async def student_trends(student_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession) -> TrendsOut:
    """The last 12 weeks (first answers, how many right, minutes), how well each subject, question
    format and difficulty goes, and the scores of the last 20 tests - for the charts of Progress."""
    return await dashboard_service.trends(db, principal, student_id)
