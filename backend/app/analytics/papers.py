"""The numbers of a previous-year paper analysis - no database, no AI (spec §46 Phase 3 item 1).

From the questions of the analysed papers: where the marks go (by chapter of the textbooks, with a
trend over the years), the topics asked most, the kinds of questions, the layout of the latest paper -
and the plan of a test in that layout, its questions spread over the chapters by their marks.

A question whose marks the paper does not show counts as 1 mark; one no textbook chapter teaches
counts towards the papers' marks but no chapter's. Like the other rules, the numbers are starting
values to tune.
"""

import uuid
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from statistics import mean
from typing import Literal

from app.core.enums import QuestionFormat
from app.question_generation import paper
from app.question_generation.schemas import WRITTEN_FORMATS

TOPICS_SHOWN = 10
_TREND_STEP = 0.25  # of a chapter's average marks: a change smaller than this is "steady"

Trend = Literal["rising", "falling", "steady"]


@dataclass(frozen=True, slots=True)
class Paper:
    document_id: uuid.UUID
    year: int | None
    duration_minutes: int | None
    negative_marks: float
    uploaded_at: datetime  # orders papers that show no year


@dataclass(frozen=True, slots=True)
class Asked:
    """One question of an analysed paper, in the paper's order."""

    document_id: uuid.UUID
    section: str
    marks: float | None
    format: str
    chapter_id: uuid.UUID | None
    topic_id: uuid.UUID | None

    @property
    def weight(self) -> float:
        return self.marks or 1


@dataclass(slots=True)
class ChapterWeight:
    chapter_id: uuid.UUID
    questions: int = 0
    marks: float = 0
    papers: set[uuid.UUID] = field(default_factory=set)
    by_paper: dict[uuid.UUID, float] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PatternSection:
    title: str
    questions: int
    marks: int  # each
    formats: tuple[str, ...]  # most frequent first


def dated(papers: Sequence[Paper]) -> list[Paper]:
    """The papers that show their year, oldest first."""
    return sorted((p for p in papers if p.year is not None), key=lambda p: (p.year, p.uploaded_at))


def latest(papers: Sequence[Paper]) -> Paper:
    return max(papers, key=lambda p: (p.year is not None, p.year or 0, p.uploaded_at))


def chapters(questions: Sequence[Asked]) -> list[ChapterWeight]:
    """Every chapter asked, most marks first."""
    weights: dict[uuid.UUID, ChapterWeight] = {}
    for q in questions:
        if q.chapter_id is None:
            continue
        chapter = weights.setdefault(q.chapter_id, ChapterWeight(q.chapter_id))
        chapter.questions += 1
        chapter.marks += q.weight
        chapter.papers.add(q.document_id)
        chapter.by_paper[q.document_id] = chapter.by_paper.get(q.document_id, 0) + q.weight
    return sorted(weights.values(), key=lambda c: (-c.marks, -c.questions))


def trend(marks: Sequence[float]) -> Trend | None:
    """A chapter's marks in the dated papers, oldest first: the newer half against the older half.
    None with fewer than three dated papers."""
    if len(marks) < 3:
        return None
    half = len(marks) // 2
    change = mean(marks[-half:]) - mean(marks[:half])
    step = max(1.0, _TREND_STEP * mean(marks))
    return "rising" if change >= step else "falling" if change <= -step else "steady"


def topics(questions: Sequence[Asked]) -> list[tuple[uuid.UUID, uuid.UUID, int, int]]:
    """(chapter, topic, questions, papers) of the topics asked most."""
    asked = Counter((q.chapter_id, q.topic_id) for q in questions if q.chapter_id and q.topic_id)
    papers: dict[tuple, set[uuid.UUID]] = {}
    for q in questions:
        papers.setdefault((q.chapter_id, q.topic_id), set()).add(q.document_id)
    ranked = sorted(asked, key=lambda key: (-len(papers[key]), -asked[key]))
    return [(c, t, asked[(c, t)], len(papers[(c, t)])) for c, t in ranked[:TOPICS_SHOWN]]


def formats(questions: Sequence[Asked]) -> list[tuple[str, int, float]]:
    """(format, questions, marks), the most asked first."""
    counted = Counter(q.format for q in questions)
    marks = Counter[str]()
    for q in questions:
        marks[q.format] += q.weight
    return [(name, count, marks[name]) for name, count in counted.most_common()]


def _board_section(format_: str) -> paper.Section | None:
    """The board paper's section of a format: its marks stand in for marks a paper does not show, and
    its title names a test's section ("Section B · Short answer questions")."""
    return next((s for s in paper.SECTIONS if format_ in s.formats), None)


def pattern(questions: Sequence[Asked]) -> list[PatternSection]:
    """The sections of one paper, in order, from its questions."""
    sections: dict[str, list[Asked]] = {}
    for q in questions:
        sections.setdefault(q.section, []).append(q)
    planned = []
    for title, asked in sections.items():
        kinds = tuple(name for name, _ in Counter(q.format for q in asked).most_common())
        printed = Counter(q.marks for q in asked if q.marks)
        board = _board_section(kinds[0])
        marks = printed.most_common(1)[0][0] if printed else board.marks if board else 1
        planned.append(PatternSection(title, len(asked), max(1, round(marks)), kinds))
    return planned


def _fit(kinds: Sequence[str], allowed: Sequence[str]) -> list[str]:
    """The formats of a section the class can be given; an objective section the class has none of
    becomes multiple choice."""
    kept = [k for k in kinds if k in allowed]
    if not kept and not set(kinds) & WRITTEN_FORMATS and QuestionFormat.MCQ in allowed:
        kept = [QuestionFormat.MCQ.value]
    return kept


def test_sections(
    layout: Sequence[PatternSection],
    weights: Sequence[ChapterWeight],
    *,
    count: int,
    negative_marks: float,
    allowed: Sequence[str],
) -> list[dict]:
    """A test of `count` questions in the paper's layout (its sections in order, with their marks),
    each section spread over the chapters by their marks. Same shape as `paper.sections`, plus
    `chapters`."""
    fitted = [(s, f) for s in layout if (f := _fit(s.formats, allowed))]
    if not fitted or not weights:
        return []
    planned = []
    for (section, kinds), n in zip(
        fitted, paper.spread(count, [s.questions for s, _ in fitted]), strict=True
    ):
        if not n:
            continue
        shares = paper.spread(n, [c.marks for c in weights])
        board = _board_section(kinds[0])
        planned.append(
            {
                "code": chr(ord("A") + len(planned)),
                "title": board.title if board else "Questions",
                "marks": section.marks,
                "negative": 0 if set(kinds) & WRITTEN_FORMATS else negative_marks,
                "count": n,
                "formats": kinds,
                "chapters": {str(c.chapter_id): k for c, k in zip(weights, shares, strict=True) if k},
            }
        )
    return planned


def minutes_per_mark(latest_paper: Paper, questions: Sequence[Asked]) -> float:
    """The latest paper's pace, when it shows its time; a board paper's otherwise."""
    marks = sum(q.weight for q in questions if q.document_id == latest_paper.document_id)
    if latest_paper.duration_minutes and marks:
        return latest_paper.duration_minutes / marks
    return paper.MINUTES_PER_MARK
