"""Mastery, recommendations and misconceptions of one learner, for whoever may see that learner (404
otherwise)."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.adaptive_learning import mastery, misconceptions, recommendations
from app.auth.principal import Principal
from app.models import Student
from app.schemas.adaptive import MasteryOut, MisconceptionsOut, RecommendationsOut
from app.services import library_service, student_service

LISTED = 50  # misconceptions listed, active first


async def _learner(db: AsyncSession, principal: Principal, student_id: uuid.UUID) -> Student:
    return student_service.require_profile(await student_service.get_student(db, principal, student_id))


async def knowledge_profile(db: AsyncSession, principal: Principal, student_id: uuid.UUID) -> MasteryOut:
    return await mastery.knowledge_profile(db, await _learner(db, principal, student_id))


async def recommendations_for_today(
    db: AsyncSession, principal: Principal, student_id: uuid.UUID
) -> RecommendationsOut:
    student = await _learner(db, principal, student_id)
    owner = await student_service.account_of(db, student)
    return await recommendations.for_today(db, student, library_service.books_for_learner(owner, student.id))


async def misconceptions_of(
    db: AsyncSession, principal: Principal, student_id: uuid.UUID
) -> MisconceptionsOut:
    return await misconceptions.of_learner(db, await _learner(db, principal, student_id), limit=LISTED)
