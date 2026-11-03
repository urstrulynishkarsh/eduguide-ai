"""The study planner's rules: the tasks from today to the exam, from what the learner knows.

Rules, not the AI - free, instant and predictable. For each chapter the exam covers, in book order:

* a weak area (below 60% right over at least 5 answers): learn the idea again, then practise at its
  lowered level. These come first of all;
* a chapter never practised: learn the idea, then practise;
* a chapter below the target: practise at its level, as many times as it needs to get there (about
  one practice for every 25 points of mastery it lacks). The second and later practices come in
  rounds through the chapters, so the practice of one chapter is spread out;
* a chapter at or above the target: one review practice, in the last days;
* the last day: a test of each book - a full mock test where the class has them, otherwise a practice
  test (none for Nursery - Class 2).

Tasks take minutes. The final ones are placed from the last day backwards (the tests on the very
last), the rest spread evenly over the days before, within the minutes a day; a task always fits an
empty day. What does not fit before the exam is counted, not squeezed in. The service plans the
remaining days again each morning from the latest mastery (services/study_plan_service.py), so the
plan follows performance. The minutes are starting values to tune, like those of docs/07 §7.4.
"""

import math
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field

LEARN_MINUTES = 15
PRACTICE_MINUTES = 20
GAIN = 0.25  # about how much one practice raises a chapter's mastery

_TEST_REASON = {
    "full_mock": "A full mock test, timed like the exam.",
    "practice": "A practice test on the whole book.",
}


@dataclass(frozen=True, slots=True)
class WeakArea:
    topic_id: uuid.UUID | None  # None: the chapter in general
    difficulty: str
    right_lately: str  # e.g. "33% right in the last 6 answers"


@dataclass(frozen=True, slots=True)
class Chapter:
    book_id: uuid.UUID
    chapter_id: uuid.UUID
    mastery: float | None  # None: never practised
    difficulty: str  # for a practice of the whole chapter
    weak: Sequence[WeakArea] = ()
    learnt: frozenset[uuid.UUID | None] = field(default_factory=frozenset)  # areas learnt in this plan


@dataclass(frozen=True, slots=True)
class FinalTest:
    kind: str  # full_mock | practice
    minutes: int


@dataclass(frozen=True, slots=True)
class Task:
    kind: str  # learn | practice | test
    book_id: uuid.UUID
    chapter_id: uuid.UUID | None
    topic_id: uuid.UUID | None
    difficulty: str
    minutes: int
    reason: str


@dataclass(frozen=True, slots=True)
class Placed:
    day: int  # 0 = today
    task: Task


def _task(
    chapter: Chapter, kind: str, topic: uuid.UUID | None, difficulty: str, minutes: int, reason: str
) -> Task:
    return Task(kind, chapter.book_id, chapter.chapter_id, topic, difficulty, minutes, reason)


def _practices_needed(mastery: float | None, target: float) -> int:
    """How many practices take a chapter below the target there (at least one)."""
    return max(1, math.ceil(round((target - (mastery or 0.0)) / GAIN, 6)))


def tasks(
    chapters: Sequence[Chapter], *, target: float, final_test: FinalTest | None
) -> tuple[list[Task], list[Task]]:
    """The work, in the order to do it, and the final stretch (reviews, then the tests)."""
    weak: list[Task] = []
    work: list[Task] = []
    again: list[tuple[int, Task]] = []  # (round, task): the practices after a chapter's first
    final: list[Task] = []
    aim = f"the aim is {round(target * 100)}%"
    for chapter in chapters:
        for area in chapter.weak:
            if area.topic_id not in chapter.learnt:
                reason = f"{area.right_lately}. Revise the idea."
                weak.append(_task(chapter, "learn", area.topic_id, "mixed", LEARN_MINUTES, reason))
            reason = f"Then strengthen it with {area.difficulty} questions."
            weak.append(_task(chapter, "practice", area.topic_id, area.difficulty, PRACTICE_MINUTES, reason))
        if chapter.mastery is not None and chapter.mastery >= target:
            reason = f"{round(chapter.mastery * 100)}% mastered. A quick review before the exam."
            final.append(_task(chapter, "practice", None, chapter.difficulty, PRACTICE_MINUTES, reason))
            continue
        if chapter.mastery is None:
            if None not in chapter.learnt:
                reason = "Not practised yet. Learn the idea first."
                work.append(_task(chapter, "learn", None, "mixed", LEARN_MINUTES, reason))
            reason = "A first practice of this chapter."
            work.append(_task(chapter, "practice", None, chapter.difficulty, PRACTICE_MINUTES, reason))
        elif not any(area.topic_id is None for area in chapter.weak):  # a weak chapter is practised above
            reason = f"{round(chapter.mastery * 100)}% mastered; {aim}."
            work.append(_task(chapter, "practice", None, chapter.difficulty, PRACTICE_MINUTES, reason))
        reason = f"More practice: {aim}."
        for round_ in range(1, _practices_needed(chapter.mastery, target)):
            again.append(
                (round_, _task(chapter, "practice", None, chapter.difficulty, PRACTICE_MINUTES, reason))
            )
    if final_test is not None:
        for book_id in dict.fromkeys(chapter.book_id for chapter in chapters):
            final.append(
                Task("test", book_id, None, None, "mixed", final_test.minutes, _TEST_REASON[final_test.kind])
            )
    again.sort(key=lambda planned: planned[0])  # stable: book order inside each round
    return weak + work + [task for _, task in again], final


def schedule(
    work: Sequence[Task], final: Sequence[Task], *, days: int, daily_minutes: int, booked: dict[int, int]
) -> tuple[list[Placed], int]:
    """Places the tasks on days 0 .. days-1, where `booked` minutes are already taken. Returns the
    placements in day order and how many tasks did not fit."""
    load = [booked.get(day, 0) for day in range(days)]

    def fits(day: int, minutes: int) -> bool:
        return load[day] == 0 or load[day] + minutes <= daily_minutes

    placed: list[tuple[int, int, Task]] = []  # (day, order, task)
    unscheduled = 0
    day = days - 1
    for order, task in reversed(list(enumerate(final, start=len(work)))):
        while day >= 0 and not fits(day, task.minutes):
            day -= 1
        if day < 0:
            unscheduled += 1
            continue
        load[day] += task.minutes
        placed.append((day, order, task))

    last = min((day for day, _, _ in placed), default=days - 1)
    open_days = [day for day in range(last + 1) if load[day] < daily_minutes]
    total = sum(task.minutes for task in work)
    done = index = 0
    for order, task in enumerate(work):
        # Evenly: a task starts on the day its share of the work falls on, or later when that is full.
        index = max(index, done * len(open_days) // total)
        while index < len(open_days) and not fits(open_days[index], task.minutes):
            index += 1
        if index == len(open_days):
            unscheduled += 1
            continue
        load[open_days[index]] += task.minutes
        placed.append((open_days[index], order, task))
        done += task.minutes
    placed.sort(key=lambda p: (p[0], p[1]))
    return [Placed(day, task) for day, _, task in placed], unscheduled
