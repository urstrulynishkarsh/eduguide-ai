"""The numbers of a previous-year paper analysis, and the codes the AI chooses chapters by."""

import uuid
from datetime import UTC, datetime

from app.analytics import paper_reading
from app.analytics import papers as numbers

OLD, NEW = uuid.uuid4(), uuid.uuid4()
ALGEBRA, GEOMETRY = uuid.uuid4(), uuid.uuid4()


def _asked(paper: uuid.UUID, section: str, marks: float | None, fmt: str, chapter: uuid.UUID | None):
    return numbers.Asked(paper, section, marks, fmt, chapter, None)


QUESTIONS = [
    _asked(OLD, "Section A", 1, "mcq", ALGEBRA),
    _asked(OLD, "Section B", 3, "short_answer", GEOMETRY),
    _asked(NEW, "Section A", 1, "mcq", ALGEBRA),
    _asked(NEW, "Section A", None, "assertion_reason", None),  # no marks shown, no chapter
    _asked(NEW, "Section B", 5, "long_answer", ALGEBRA),
]


def test_chapters_by_marks():
    algebra, geometry = numbers.chapters(QUESTIONS)
    assert (algebra.chapter_id, algebra.questions, algebra.marks, len(algebra.papers)) == (ALGEBRA, 3, 7, 2)
    assert algebra.by_paper == {OLD: 1, NEW: 6}
    assert (geometry.chapter_id, geometry.marks) == (GEOMETRY, 3)


def test_the_trend_compares_the_newer_papers_with_the_older():
    assert numbers.trend([2, 8]) is None  # fewer than three papers
    assert numbers.trend([2, 4, 8]) == "rising"
    assert numbers.trend([8, 8, 2, 2]) == "falling"
    assert numbers.trend([5, 6, 5]) == "steady"  # within a quarter of its average marks


def test_the_layout_of_a_paper():
    layout = numbers.pattern([q for q in QUESTIONS if q.document_id == NEW])
    assert layout == [
        numbers.PatternSection("Section A", 2, 1, ("mcq", "assertion_reason")),
        numbers.PatternSection("Section B", 1, 5, ("long_answer",)),
    ]
    # A section without printed marks gets a board paper's marks for its format.
    assert numbers.pattern([_asked(NEW, "Part 1", None, "long_answer", None)])[0].marks == 5


def test_a_test_like_the_paper_spreads_each_section_over_the_chapters_by_marks():
    layout = [
        numbers.PatternSection("Section A", 6, 1, ("mcq", "fill_blank")),
        numbers.PatternSection("Section B", 3, 2, ("true_false",)),
        numbers.PatternSection("Section C", 2, 5, ("long_answer",)),
    ]
    weights = numbers.chapters(QUESTIONS)
    planned = numbers.test_sections(
        layout, weights, count=11, negative_marks=1, allowed=("mcq", "short_answer", "long_answer")
    )
    assert [
        (s["code"], s["title"], s["formats"], s["negative"], s["count"], s["chapters"]) for s in planned
    ] == [
        ("A", "Objective questions", ["mcq"], 1, 6, {str(ALGEBRA): 4, str(GEOMETRY): 2}),
        # True / false is not for the class: multiple choice instead.
        ("B", "Objective questions", ["mcq"], 1, 3, {str(ALGEBRA): 2, str(GEOMETRY): 1}),
        # Written answers lose no marks.
        ("C", "Long answer questions", ["long_answer"], 0, 2, {str(ALGEBRA): 1, str(GEOMETRY): 1}),
    ]
    assert numbers.test_sections(layout, [], count=5, negative_marks=0, allowed=("mcq",)) == []


def test_pace_and_the_latest_paper():
    at = datetime(2026, 1, 1, tzinfo=UTC)
    old = numbers.Paper(OLD, 2022, None, 0, at)
    new = numbers.Paper(NEW, 2023, 70, 0, at)
    assert numbers.latest([new, old]) is new
    assert numbers.latest([old, numbers.Paper(NEW, None, None, 0, at)]) is old  # a year beats none
    assert numbers.minutes_per_mark(new, QUESTIONS) == 10  # 70 minutes, 7 marks (1 + 1 + 5)
    assert numbers.minutes_per_mark(old, QUESTIONS) == 2  # no time shown: a board paper's pace


def test_area_codes_and_years():
    listed = paper_reading.areas(
        [("Chapter 1 Algebra", ["1.1 Terms", "1.2 Equations"]), ("Chapter 2 Shapes", [])]
    )
    assert [(a.code, a.label, a.chapter_index, a.topic_index) for a in listed] == [
        ("C1", "Chapter 1 Algebra", 0, None),
        ("C1.1", "1.1 Terms", 0, 0),
        ("C1.2", "1.2 Equations", 0, 1),
        ("C2", "Chapter 2 Shapes", 1, None),
    ]
    assert paper_reading.year_from("CBSE-2023-Maths.pdf") == 2023
    assert paper_reading.year_from("papers 2022 and 2023.pdf") is None  # two years: unclear
    assert paper_reading.year_from("sample.pdf") is None
