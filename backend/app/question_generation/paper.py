"""A test paper: which tests a class may take, its sections and marks, and its time (docs/07 §7.6).

Sections follow a board paper: objective questions first, then numerical problems, short answers and
long answers. A section is left out when the class uses none of its formats (Class 3-5 have no
numerical or long answers). Like the limits in docs/07 §7.4, the numbers are starting values to tune.
"""

from dataclasses import dataclass
from typing import Literal

from app.class_profiles import ClassProfile
from app.core.enums import QuestionFormat as F

TestKind = Literal["practice", "chapter", "full_mock"]

# The class-profile switch each kind of test needs.
FEATURE: dict[str, str] = {
    "practice": "practice_tests",
    "chapter": "chapter_tests",
    "full_mock": "full_mock_tests",
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


def allowed(profile: ClassProfile, kind: str) -> bool:
    return getattr(profile.features, FEATURE[kind])


def default_count(profile: ClassProfile, kind: str) -> int:
    wanted = DEFAULT_QUESTIONS.get(kind, profile.default_session_questions)
    return min(wanted, profile.max_session_questions)


def sections(profile: ClassProfile, count: int) -> list[dict]:
    """The paper's plan for `count` questions: every section the class has gets at least one question
    (the first ones, when there are fewer questions than sections), the rest by share."""
    present = [
        (section, [f for f in section.formats if f in profile.question_formats])
        for section in SECTIONS
        if set(section.formats) & set(profile.question_formats)
    ][:count]
    weights = [section.share for section, _ in present]
    extra = [(count - len(present)) * w / sum(weights) for w in weights]
    counts = [1 + int(e) for e in extra]
    by_remainder = sorted(range(len(present)), key=lambda i: extra[i] - int(extra[i]), reverse=True)
    for i in by_remainder[: count - sum(counts)]:
        counts[i] += 1
    return [
        {"code": s.code, "title": s.title, "marks": s.marks, "count": n, "formats": formats}
        for (s, formats), n in zip(present, counts, strict=True)
    ]


def minutes(planned: list[dict]) -> int:
    """About how long the paper takes, rounded up to 5 minutes."""
    marks = sum(section["marks"] * section["count"] for section in planned)
    return -(-marks * MINUTES_PER_MARK // 5) * 5
