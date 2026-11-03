"""The study planner: one plan per learner, daily tasks that follow performance."""

import uuid

from fastapi import APIRouter, Response, status

from app.api.deps import CurrentPrincipal, DbSession
from app.schemas.study_plan import PlanItemOut, PlanItemUpdate, StudyPlanCreate, StudyPlanOut
from app.services import study_plan_service

router = APIRouter(tags=["Study planner"])


@router.post(
    "/study-plans", response_model=StudyPlanOut, status_code=status.HTTP_201_CREATED, summary="Make a plan"
)
async def create_plan(data: StudyPlanCreate, principal: CurrentPrincipal, db: DbSession) -> StudyPlanOut:
    """From today to the exam, within the minutes a day: weak topics first, new chapters (learn, then
    practise), more practice below the target, reviews and a test of each book at the end. Replaces
    the learner's plan if they have one. Not in child mode."""
    return await study_plan_service.create_plan(db, principal, data)


@router.get("/students/{student_id}/study-plan", response_model=StudyPlanOut, summary="A learner's plan")
async def get_plan(student_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession) -> StudyPlanOut:
    """By day. On the first visit of a day the remaining days are planned again from the latest
    mastery; tasks of past days still pending become `missed`."""
    return await study_plan_service.get_plan(db, principal, student_id)


@router.patch("/study-plan-items/{item_id}", response_model=PlanItemOut, summary="Tick a task off")
async def update_item(
    item_id: uuid.UUID, data: PlanItemUpdate, principal: CurrentPrincipal, db: DbSession
) -> PlanItemOut:
    """done, skipped or pending again. Practice and test tasks are also ticked off by finishing them."""
    return await study_plan_service.update_item(db, principal, item_id, data.status)


@router.delete("/study-plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Remove a plan")
async def delete_plan(plan_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession) -> Response:
    await study_plan_service.delete_plan(db, principal, plan_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
