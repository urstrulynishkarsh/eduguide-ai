"""The rules of XP levels and streaks."""

from datetime import date, timedelta

import pytest

from app.analytics.rewards import level_of, shown_streak, streak_on

DAY = date(2026, 11, 4)
YESTERDAY = DAY - timedelta(days=1)


@pytest.mark.parametrize(
    ("xp", "level"),
    [(0, (1, 0, 100)), (99, (1, 99, 100)), (100, (2, 0, 150)), (249, (2, 149, 150)), (700, (5, 0, 300))],
)
def test_each_level_takes_50_xp_more_than_the_one_before(xp, level):
    assert level_of(xp) == level


def test_a_streak_grows_once_a_day_and_starts_again_after_a_missed_day():
    assert streak_on(DAY, 0, None) == 1  # the first answer ever
    assert streak_on(DAY, 4, YESTERDAY) == 5
    assert streak_on(DAY, 5, DAY) == 5  # another answer the same day
    assert streak_on(DAY, 5, DAY - timedelta(days=2)) == 1


def test_a_streak_is_kept_until_the_end_of_the_next_day():
    assert shown_streak(DAY, 3, DAY) == 3
    assert shown_streak(DAY, 3, YESTERDAY) == 3  # still time to answer today
    assert shown_streak(DAY, 3, DAY - timedelta(days=2)) == 0
    assert shown_streak(DAY, 0, None) == 0
