"""Which tests a class may take, and how a paper is cut into sections."""

import pytest

from app.class_profiles import get_class_profile
from app.core.enums import ClassLevel
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
        ("class_10", ["practice", "chapter", "full_mock"]),
        ("class_12", ["practice", "chapter", "full_mock"]),
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
