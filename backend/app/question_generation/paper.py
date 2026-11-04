"""A test paper: which tests a class may take, its sections and marks, and its time (docs/07 §7.6).

Sections follow a board paper: objective questions first, then numerical problems, short answers and
long answers. A section is left out when the class uses none of its formats (Class 3-5 have no
numerical or long answers). Like the limits in docs/07 §7.4, the numbers are starting values to tune.

JEE / NEET / CUET mode: a Class 11-12 learner whose goal is one of them takes every test in that
exam's pattern - its sections, its marks and negative marks, its pace (spec §9; NTA's 2026 patterns,
to be checked against each year's information bulletin).
"""

import math
from dataclasses import dataclass
from typing import Literal

from app.class_profiles import ClassProfile
from app.core.enums import Goal
from app.core.enums import QuestionFormat as F

# previous_year: a test in the pattern of the previous-year papers of a book (services/paper_analysis_service)
TestKind = Literal["practice", "chapter", "full_mock", "previous_year"]

# The class-profile switch each kind of test needs.
FEATURE: dict[str, str] = {
    "practice": "practice_tests",
    "chapter": "chapter_tests",
    "full_mock": "full_mock_tests",
    "previous_year": "previous_year_questions",
}
DEFAULT_QUESTIONS: dict[str, int] = {"chapter": 15, "full_mock": 30}  # practice: the class's usual number
MINUTES_PER_MARK = 2  # about a board paper's pace (80 marks in 3 hours)


@dataclass(frozen=True, slots=True)
class Section:
    code: str
    title: str
    formats: tuple[F, ...]
    marks: int  # for each question
    share: float  # of the paper's questions
    negative: float = 0  # marks lost for a wrong answer


@dataclass(frozen=True, slots=True)
class Pattern:
    sections: tuple[Section, ...]
    minutes_per_mark: float
    # A board paper has every section; an exam keeps its own ratio (JEE: 20 MCQs to 5 numericals).
    every_section: bool = False


SECTIONS = (
    Section(
        "A",
        "Objective questions",
        (F.MCQ, F.TRUE_FALSE, F.FILL_BLANK, F.ASSERTION_REASON, F.CASE_BASED),
        1,
        0.5,
    ),
    Section("B", "Numerical problems", (F.NUMERICAL,), 2, 0.15),
    Section("C", "Short answer questions", (F.SHORT_ANSWER,), 2, 0.2),
    Section("D", "Long answer questions", (F.LONG_ANSWER,), 5, 0.15),
)
BOARD = Pattern(SECTIONS, MINUTES_PER_MARK, every_section=True)

_OBJECTIVE = "Objective questions"
EXAMS: dict[Goal, Pattern] = {
    # Per subject: 20 MCQs and 5 numerical answers, +4 / -1 each; 75 questions (300 marks) in 3 hours.
    Goal.JEE: Pattern(
        (
            Section("A", _OBJECTIVE, (F.MCQ, F.ASSERTION_REASON), 4, 0.8, negative=1),
            Section("B", "Numerical problems", (F.NUMERICAL,), 4, 0.2, negative=1),
        ),
        180 / 300,
    ),
    # 180 MCQs, +4 / -1; 720 marks in 3 hours.
    Goal.NEET: Pattern((Section("A", _OBJECTIVE, (F.MCQ, F.ASSERTION_REASON), 4, 1, negative=1),), 180 / 720),
    # Per domain subject: 50 MCQs, +5 / -1, in 60 minutes.
    Goal.CUET: Pattern(
        (Section("A", _OBJECTIVE, (F.MCQ, F.ASSERTION_REASON, F.CASE_BASED), 5, 1, negative=1),), 60 / 250
    ),
}


def allowed(profile: ClassProfile, kind: str) -> bool:
    return getattr(profile.features, FEATURE[kind])


def exam_for(profile: ClassProfile, goal: str) -> Goal | None:
    """The exam whose pattern a learner's tests follow: their goal, where the class has exam modes."""
    return Goal(goal) if profile.features.competitive_exam_modes and goal in EXAMS else None


def pattern_for(profile: ClassProfile, goal: str) -> Pattern:
    exam = exam_for(profile, goal)
    return EXAMS[exam] if exam else BOARD


def default_count(profile: ClassProfile, kind: str) -> int:
    wanted = DEFAULT_QUESTIONS.get(kind, profile.default_session_questions)
    return min(wanted, profile.max_session_questions)


def spread(count: int, weights: list[float], *, at_least_one: bool = False) -> list[int]:
    """`count` shared out by weight, the rest of the division going to the largest remainders.
    `at_least_one`: every weight gets one first (there must be at least as many as weights)."""
    floor = 1 if at_least_one else 0
    extra = [(count - floor * len(weights)) * w / sum(weights) for w in weights]
    counts = [floor + int(e) for e in extra]
    by_remainder = sorted(range(len(weights)), key=lambda i: extra[i] - int(extra[i]), reverse=True)
    for i in by_remainder[: count - sum(counts)]:
        counts[i] += 1
    return counts


def sections(profile: ClassProfile, count: int, pattern: Pattern = BOARD) -> list[dict]:
    """The paper's plan for `count` questions, in the sections the class has formats for. Board pattern:
    every section gets at least one question (the first ones, when there are fewer questions than
    sections), the rest by share. An exam pattern: all by share."""
    present = [
        (section, [f for f in section.formats if f in profile.question_formats])
        for section in pattern.sections
        if set(section.formats) & set(profile.question_formats)
    ]
    if pattern.every_section:
        present = present[:count]
    counts = spread(count, [section.share for section, _ in present], at_least_one=pattern.every_section)
    return [
        {
            "code": s.code,
            "title": s.title,
            "marks": s.marks,
            "negative": s.negative,
            "count": n,
            "formats": formats,
        }
        for (s, formats), n in zip(present, counts, strict=True)
        if n
    ]


def minutes(planned: list[dict], minutes_per_mark: float = MINUTES_PER_MARK) -> int:
    """About how long the paper takes, rounded up to 5 minutes."""
    marks = sum(section["marks"] * section["count"] for section in planned)
    return math.ceil(round(marks * minutes_per_mark / 5, 6)) * 5
