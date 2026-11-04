"""The study planner's rules: which tasks, in which order, on which days."""

import uuid

from app.adaptive_learning import planner
from app.adaptive_learning.planner import Chapter, FinalTest, Task, WeakArea

BOOK, OTHER_BOOK = uuid.uuid4(), uuid.uuid4()
TOPIC = uuid.uuid4()


def _chapter(mastery: float | None = None, **values) -> Chapter:
    return Chapter(book_id=BOOK, chapter_id=uuid.uuid4(), mastery=mastery, difficulty="medium", **values)


def _kinds(tasks: list[Task]) -> list[tuple[str, dict]]:
    return [(task.kind, task.reason) for task in tasks]


def test_weak_areas_come_first_then_the_chapters_in_book_order():
    below = _chapter(0.5)
    new = _chapter()
    weak = _chapter(0.4, weak=[WeakArea(TOPIC, "easy", {"accuracy": 0.2, "answers": 5})])

    work, final = planner.tasks([below, new, weak], target=0.8, final_test=None)

    assert _kinds(work)[:6] == [
        ("learn", {"code": "revise", "accuracy": 0.2, "answers": 5}),
        ("practice", {"code": "strengthen", "difficulty": "easy"}),
        ("practice", {"code": "towards_aim", "mastery": 0.5, "aim": 0.8}),
        ("learn", {"code": "learn_first"}),
        ("practice", {"code": "first_practice"}),
        ("practice", {"code": "towards_aim", "mastery": 0.4, "aim": 0.8}),  # the weak chapter's other topics
    ]
    assert (work[0].topic_id, work[1].difficulty) == (TOPIC, "easy")
    assert work[5].chapter_id == weak.chapter_id and final == []


def test_a_chapter_gets_the_practices_it_needs_to_reach_the_target_spread_in_rounds():
    below, new, nearly = _chapter(0.5), _chapter(), _chapter(0.7)

    work, _ = planner.tasks([below, new, nearly], target=0.8, final_test=None)

    # 30 points short: 2 practices; never practised: 4 (after learning); 10 points short: 1.
    order = {below.chapter_id: "below", new.chapter_id: "new", nearly.chapter_id: "nearly"}
    assert [(order[task.chapter_id], task.kind) for task in work] == [
        ("below", "practice"),
        ("new", "learn"),
        ("new", "practice"),
        ("nearly", "practice"),
        ("below", "practice"),  # round 2
        ("new", "practice"),
        ("new", "practice"),  # round 3
        ("new", "practice"),  # round 4
    ]
    assert work[4].reason == {"code": "more_practice", "aim": 0.8}


def test_strong_chapters_are_reviewed_at_the_end_and_each_book_ends_with_a_test():
    strong = _chapter(0.9)
    other = Chapter(book_id=OTHER_BOOK, chapter_id=uuid.uuid4(), mastery=None, difficulty="mixed")

    work, final = planner.tasks([strong, other], target=0.8, final_test=FinalTest("full_mock", 125))

    assert [task.kind for task in work] == ["learn", "practice", "practice", "practice", "practice"]
    assert _kinds(final) == [
        ("practice", {"code": "final_review", "mastery": 0.9}),
        ("test", {"code": "full_mock_test"}),
        ("test", {"code": "full_mock_test"}),
    ]
    assert [(task.book_id, task.chapter_id, task.minutes) for task in final[1:]] == [
        (BOOK, None, 125),
        (OTHER_BOOK, None, 125),
    ]


def test_what_was_learnt_is_not_learnt_again_and_a_weak_chapter_is_practised_once():
    learnt_new = _chapter(learnt=frozenset({None}))
    weak_chapter = _chapter(0.3, weak=[WeakArea(None, "easy", {"accuracy": 0.3, "answers": 10})])

    work, _ = planner.tasks([learnt_new, weak_chapter], target=0.8, final_test=None)

    assert [(task.kind, task.chapter_id) for task in work] == [
        ("learn", weak_chapter.chapter_id),
        ("practice", weak_chapter.chapter_id),  # its first practice: the weak one
        ("practice", learnt_new.chapter_id),
        ("practice", learnt_new.chapter_id),
        ("practice", weak_chapter.chapter_id),  # 50 points short: a second one
        ("practice", learnt_new.chapter_id),
        ("practice", learnt_new.chapter_id),
    ]


def _task(minutes: int = 20, kind: str = "practice") -> Task:
    return Task(kind, BOOK, None, None, "mixed", minutes, {"code": "first_practice"})


def test_the_test_is_on_the_last_day_and_the_work_is_spread_evenly_before_it():
    work = [_task() for _ in range(4)]
    test = _task(60, "test")

    placed, unscheduled = planner.schedule(work, [test], days=10, daily_minutes=30, booked={})

    assert unscheduled == 0
    assert [(p.day, p.task.kind) for p in placed] == [
        (0, "practice"),
        (2, "practice"),
        (4, "practice"),
        (6, "practice"),
        (9, "test"),  # longer than a day's minutes: it gets a day of its own
    ]


def test_a_day_holds_its_minutes_and_what_does_not_fit_is_counted():
    placed, unscheduled = planner.schedule(
        [_task() for _ in range(5)], [], days=2, daily_minutes=40, booked={}
    )

    assert [p.day for p in placed] == [0, 0, 1, 1]
    assert unscheduled == 1


def test_minutes_already_taken_count_and_one_day_holds_the_work_before_the_test():
    placed, unscheduled = planner.schedule(
        [_task(15), _task(20)], [_task(30, "test")], days=1, daily_minutes=60, booked={0: 10}
    )
    assert [p.task.kind for p in placed] == ["practice", "test"] and unscheduled == 1  # 10 + 30 + 15 fit

    placed, _ = planner.schedule([_task()], [], days=3, daily_minutes=30, booked={0: 30})
    assert placed[0].day == 1  # today is full
