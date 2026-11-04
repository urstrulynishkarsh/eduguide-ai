"""Streaks, XP and badges (analytics/rewards.py)."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Badge = Literal[
    "first_practice",
    "perfect_practice",
    "right_10",
    "right_100",
    "streak_3",
    "streak_7",
    "streak_30",
    "first_test",
    "topic_mastered",
    "mistake_fixed",
    "level_5",
]


class BadgeOut(BaseModel):
    code: Badge
    earned_at: datetime | None = Field(description="Null: not earned yet.")


class TodayGoal(BaseModel):
    answered: int = Field(description="Questions answered today (India time), the first answer to each.")
    goal: int = Field(description="One practice's worth for the class.")


class RewardsOut(BaseModel):
    student_id: uuid.UUID
    xp: int
    level: int
    level_xp: int = Field(description="XP earned inside this level.")
    level_size: int = Field(description="XP this level takes: when `level_xp` reaches it, the next level.")
    streak: int = Field(description="Days in a row with an answer, up to today or yesterday; else 0.")
    longest_streak: int
    today: TodayGoal
    badges: list[BadgeOut] = Field(description="Every badge: the earned ones first, newest first.")


class RewardGain(BaseModel):
    """What an answer earned, shown straight away."""

    xp: int
    badges: list[Badge] = Field(description="Badges earned by it.")
