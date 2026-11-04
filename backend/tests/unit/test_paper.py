"""Which tests a class may take, and how a paper is cut into sections."""

import pytest

from app.class_profiles import get_class_profile
from app.core.enums import ClassLevel, Goal
from app.question_generation import paper


def _profile(level: str):
    return get_class_profile(ClassLevel(level))


@pytest.mark.parametrize(
    ("level", "kinds"),
    [
        ("nursery", []),
        ("class_2", []),
        ("class_4", ["practice"]),
        ("class_7", ["practice", "chapter"]),
        ("class_10", ["practice", "chapter", "full_mock", "previous_year"]),
        ("class_12", ["practice", "chapter", "full_mock", "previous_year"]),
    ],
)
def test_each_class_takes_the_tests_its_profile_allows(level: str, kinds: list[str]):
    assert [kind for kind in paper.FEATURE if paper.allowed(_profile(level), kind)] == kinds


@pytest.mark.parametrize(
    ("level", "sections"),
    [
        ("class_4", [("A", 1, 8), ("C", 2, 4)]),  # no numerical or long answers in Class 3-5
        ("class_7", [("A", 1, 6), ("C", 2, 3), ("D", 5, 3)]),
        ("class_10", [("A", 1, 5), ("B", 2, 2), ("C", 2, 3), ("D", 5, 2)]),
    ],
)
def test_sections_follow_the_formats_of_the_class(level: str, sections: list[tuple]):
    planned = paper.sections(_profile(level), 12)
    assert [(s["code"], s["marks"], s["count"]) for s in planned] == sections
    allowed = set(_profile(level).question_formats)
    assert all(set(s["formats"]) <= allowed for s in planned)


@pytest.mark.parametrize("count", [1, 2, 3, 4, 5, 9, 30, 50])
def test_every_question_is_placed_and_every_section_gets_one(count: int):
    planned = paper.sections(_profile("class_10"), count)
    assert sum(s["count"] for s in planned) == count
    assert all(s["count"] >= 1 for s in planned)
    assert len(planned) == min(count, 4)  # fewer questions than sections: the first sections


def test_default_size_and_time_of_a_paper():
    assert paper.default_count(_profile("class_4"), "practice") == 8  # the class's usual number
    assert paper.default_count(_profile("class_7"), "chapter") == 15
    assert paper.default_count(_profile("class_10"), "full_mock") == 30
    planned = paper.sections(_profile("class_10"), 30)
    marks = sum(s["marks"] * s["count"] for s in planned)
    assert marks == 61 and paper.minutes(planned) == 125  # 2 minutes a mark, up to 5 minutes


def test_the_exam_mode_follows_the_goal_from_class_11():
    assert paper.exam_for(_profile("class_12"), "jee") is Goal.JEE
    assert paper.exam_for(_profile("class_11"), "cuet") is Goal.CUET
    assert paper.exam_for(_profile("class_12"), "board_exam") is None
    assert paper.exam_for(_profile("class_10"), "jee") is None  # no exam modes before Class 11


@pytest.mark.parametrize(
    ("exam", "count", "sections", "minutes"),
    [
        # JEE Main, one subject: 20 MCQs + 5 numerical answers, 100 marks in an hour.
        (Goal.JEE, 25, [("A", 4, 1, 20), ("B", 4, 1, 5)], 60),
        (Goal.NEET, 45, [("A", 4, 1, 45)], 45),  # one subject: 180 marks, 45 minutes
        (Goal.CUET, 50, [("A", 5, 1, 50)], 60),
    ],
)
def test_exam_patterns(exam: Goal, count: int, sections: list[tuple], minutes: int):
    pattern = paper.EXAMS[exam]
    planned = paper.sections(_profile("class_12"), count, pattern)
    assert [(s["code"], s["marks"], s["negative"], s["count"]) for s in planned] == sections
    assert paper.minutes(planned, pattern.minutes_per_mark) == minutes


def test_spread_shares_out_by_weight():
    assert paper.spread(5, [3, 1, 1]) == [3, 1, 1]
    assert paper.spread(3, [10, 8, 5, 1]) == [1, 1, 1, 0]  # the largest remainders get the rest
    assert paper.spread(4, [0.9, 0.1], at_least_one=True) == [3, 1]
