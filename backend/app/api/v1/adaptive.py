"""Adaptive learning: what the learner knows, the mistakes they keep making, and Recommended for You."""

import uuid

from fastapi import APIRouter

from app.api.deps import CurrentPrincipal, DbSession
from app.schemas.adaptive import MasteryOut, MisconceptionsOut, RecommendationsOut
from app.services import adaptive_service

router = APIRouter(tags=["Adaptive learning"])


@router.get("/students/{student_id}/mastery", response_model=MasteryOut, summary="Mastery by topic")
async def student_mastery(student_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession) -> MasteryOut:
    """Every topic practised (or chapter, for questions without a topic): mastery, accuracy,
    confidence, strong / learning / needs attention, and the difficulty for the next practice there."""
    return await adaptive_service.knowledge_profile(db, principal, student_id)


@router.get(
    "/students/{student_id}/recommendations",
    response_model=RecommendationsOut,
    summary="Recommended for You, today",
)
async def student_recommendations(
    student_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession
) -> RecommendationsOut:
    """At most three, kept for the day: strengthen a weak topic (with a concept revision), continue
    one being learned, review one not practised for a week, or start a new chapter. Each carries the
    body for POST /practice/sessions; finishing that practice marks it `done`."""
    return await adaptive_service.recommendations_for_today(db, principal, student_id)


@router.get(
    "/students/{student_id}/misconceptions", response_model=MisconceptionsOut, summary="Misconceptions"
)
async def student_misconceptions(
    student_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession
) -> MisconceptionsOut:
    """Wrong ideas the learner keeps showing, found by the AI in their wrong answers (Class 3-12): active
    ones first, then the ones put right (`resolved`: the area's last 3 answers right). Each carries the
    body for POST /practice/sessions (its questions check the mistake) and for POST /learn/explain."""
    return await adaptive_service.misconceptions_of(db, principal, student_id)
