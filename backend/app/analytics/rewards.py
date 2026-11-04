"""Streaks, XP and badges (spec Phase 3, item 5): the rules, and the two calls the services make.

XP is for the work done. Hints never cost any: asking for one is what a stuck learner should do.

* the first answer to a question in a practice or a test sitting: +2, right the first time +8 more
* finishing a practice, submitting a test: +20
* reaching the day's goal (one practice's worth of answers for the class): +10

Each level takes a little more: 100 XP to level 2, 150 more to level 3, 200 more to level 4, ...
A streak is the days in a row (India time) with at least one answer; it is kept until the end of
the next day. A badge is earned once (BADGES, in the order they are shown). The counting is the
same for every class; Nursery - Class 2 see stars and stickers instead of XP and levels (frontend).

Everything is counted as it happens (`record`, in the transaction of the answer), never worked out
again from history, so a book deleted later takes nothing away. The numbers are starting values
to tune once children use it.
"""

import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal, get_args

from sqlalchemy import ColumnElement, exists, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.adaptive_learning import mastery
from app.adaptive_learning.recommendations import today
from app.analytics.progress import first_answers
from app.class_profiles import get_class_profile
from app.models import Student, StudentBadge, StudentMastery, StudentMisconception, StudentReward
from app.schemas.rewards import Badge, BadgeOut, RewardGain, RewardsOut, TodayGoal

ANSWER_XP, RIGHT_XP, FINISH_XP, GOAL_XP = 2, 8, 20, 10
FIRST_LEVEL, LEVEL_STEP = 100, 50
BADGES: tuple[Badge, ...] = get_args(Badge)


def level_of(xp: int) -> tuple[int, int, int]:
    """The level of this much XP, the XP earned inside it, and the XP it takes."""
    level, size = 1, FIRST_LEVEL
    while xp >= size:
        xp, level, size = xp - size, level + 1, size + LEVEL_STEP
    return level, xp, size


def streak_on(day: date, streak: int, last_active_on: date | None) -> int:
    """The streak once `day` has an answer."""
    if last_active_on == day:
        return streak
    return streak + 1 if last_active_on == day - timedelta(days=1) else 1


def shown_streak(day: date, streak: int, last_active_on: date | None) -> int:
    """The streak as it stands on `day`: lost once a whole day went by without an answer."""
    return streak if last_active_on is not None and day - last_active_on <= timedelta(days=1) else 0


def day_goal(student: Student) -> int:
    assert student.profile is not None
    return get_class_profile(student.profile.class_level).default_session_questions


@dataclass(frozen=True, slots=True)
class Work:
    """What one request did."""

    answers: int = 0  # first answers
    right: int = 0  # of those, right
    finished: Literal["practice", "test"] | None = None
    perfect: bool = False  # a practice finished with every first answer right


async def perfect_practice(db: AsyncSession, student_id: uuid.UUID, session_id: uuid.UUID) -> bool:
    first = first_answers(student_id)
    wrong = select(func.count()).where(first.c.practice_session_id == session_id, ~first.c.is_correct)
    return await db.scalar(wrong) == 0


async def _any(db: AsyncSession, *where: ColumnElement[bool]) -> bool:
    return bool(await db.scalar(select(exists().where(*where))))


async def _earned(db: AsyncSession, student: uuid.UUID, row: StudentReward, work: Work, badge: Badge) -> bool:
    match badge:
        case "first_practice" | "first_test":
            return work.finished == badge.removeprefix("first_")
        case "perfect_practice":
            return work.perfect
        case "right_10" | "right_100":
            return row.right_answers >= int(badge.removeprefix("right_"))
        case "streak_3" | "streak_7" | "streak_30":
            return row.streak >= int(badge.removeprefix("streak_"))
        case "level_5":
            return level_of(row.xp)[0] >= 5
        case "topic_mastered":
            return bool(work.answers) and await _any(
                db,
                StudentMastery.student_id == student,
                StudentMastery.attempts >= mastery.MIN_ANSWERS,
                StudentMastery.mastery >= mastery.STRONG,
            )
        case "mistake_fixed":
            return bool(work.answers) and await _any(
                db, StudentMisconception.student_id == student, StudentMisconception.status == "resolved"
            )


async def record(db: AsyncSession, student: Student, work: Work) -> RewardGain:
    """Counts `work`: XP, the streak, today's answers and new badges (not committed)."""
    await db.execute(insert(StudentReward).values(student_id=student.id).on_conflict_do_nothing())
    # Locked: two answers at once wait for each other, so XP and badges are counted once.
    row = await db.scalar(
        select(StudentReward).where(StudentReward.student_id == student.id).with_for_update()
    )
    assert row is not None
    xp = ANSWER_XP * work.answers + RIGHT_XP * work.right + (FINISH_XP if work.finished else 0)
    if work.answers:
        day, goal = today(), day_goal(student)
        before = row.day_answers if row.last_active_on == day else 0
        row.streak = streak_on(day, row.streak, row.last_active_on)
        row.longest_streak = max(row.longest_streak, row.streak)
        row.last_active_on, row.day_answers = day, before + work.answers
        if before < goal <= row.day_answers:
            xp += GOAL_XP
    row.xp += xp
    row.right_answers += work.right

    owned = set(await db.scalars(select(StudentBadge.badge).where(StudentBadge.student_id == student.id)))
    earned = [
        badge for badge in BADGES if badge not in owned and await _earned(db, student.id, row, work, badge)
    ]
    db.add_all(StudentBadge(student_id=student.id, badge=badge) for badge in earned)
    return RewardGain(xp=xp, badges=earned)


async def summary(db: AsyncSession, student: Student) -> RewardsOut:
    row = await db.get(StudentReward, student.id) or StudentReward(student_id=student.id)
    xp = row.xp or 0
    level, inside, size = level_of(xp)
    day = today()
    earned = {
        badge.badge: badge.created_at
        for badge in await db.scalars(
            select(StudentBadge)
            .where(StudentBadge.student_id == student.id)
            .order_by(StudentBadge.created_at.desc())
        )
    }
    return RewardsOut(
        student_id=student.id,
        xp=xp,
        level=level,
        level_xp=inside,
        level_size=size,
        streak=shown_streak(day, row.streak or 0, row.last_active_on),
        longest_streak=row.longest_streak or 0,
        today=TodayGoal(answered=row.day_answers if row.last_active_on == day else 0, goal=day_goal(student)),
        badges=[
            BadgeOut(code=code, earned_at=earned.get(code))
            for code in [*earned, *(code for code in BADGES if code not in earned)]
        ],
    )
