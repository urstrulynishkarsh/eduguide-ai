"""Streaks, XP and badges."""

import uuid

from fastapi import APIRouter

from app.api.deps import CurrentPrincipal, DbSession
from app.schemas.rewards import RewardsOut
from app.services import adaptive_service

router = APIRouter(tags=["Rewards"])


@router.get("/students/{student_id}/rewards", response_model=RewardsOut, summary="Streak, XP and badges")
async def student_rewards(student_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession) -> RewardsOut:
    """XP and the level it makes, the streak (days in a row with an answer, India time), today's
    answers against the day's goal, and every badge (earned ones first). Counted as the learner
    works: the first answer to a question +2, right the first time +8 more, a finished practice or a
    submitted test +20, the day's goal +10."""
    return await adaptive_service.rewards_of(db, principal, student_id)
