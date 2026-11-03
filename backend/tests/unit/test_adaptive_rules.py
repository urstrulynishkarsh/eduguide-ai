"""The rules of adaptive learning: credit, mastery, the level rule of docs/07 §7.9, and status."""

from datetime import UTC, datetime

import pytest

from app.adaptive_learning.mastery import Answer, credit, mastery, next_level, status
from app.class_profiles import ClassFeatures
from app.models import StudentMastery

NOW = datetime(2026, 11, 3, tzinfo=UTC)


def answer(
    correct: bool = True, *, hints: int = 0, solution: bool = False, difficulty: str = "medium"
) -> Answer:
    return Answer(correct, hints, solution, difficulty, NOW)


def answers(right: int, wrong: int) -> list[Answer]:
    return [answer(True)] * right + [answer(False)] * wrong


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        (answer(), 1.0),
        (answer(hints=1), 0.75),
        (answer(hints=2), 0.5),
        (answer(hints=1, solution=True), 0.25),
        (answer(False), 0.0),
    ],
)
def test_help_opened_before_answering_lowers_the_credit(given: Answer, expected: float):
    assert credit(given) == expected


def test_recent_answers_and_harder_questions_count_more():
    assert mastery(answers(10, 0)) == 1.0
    assert mastery([answer(True), answer(False)]) > mastery([answer(False), answer(True)])  # newest first
    hard_right = [answer(True, difficulty="hard"), answer(False, difficulty="easy")]
    easy_right = [answer(True, difficulty="easy"), answer(False, difficulty="hard")]
    assert mastery(hard_right) > 0.5 > mastery(easy_right)


@pytest.mark.parametrize(
    ("level", "since_last_move", "expected"),
    [
        ("medium", answers(4, 0), "medium"),  # fewer than 5 answers: never decided on so little
        ("medium", answers(5, 0), "hard"),  # above 85%: up
        ("easy", answers(9, 1), "medium"),
        ("medium", answers(8, 2), "medium"),  # 60-85%: stays
        ("medium", answers(3, 2), "medium"),  # exactly 60% stays
        ("medium", answers(2, 3), "easy"),  # below 60%: down
        ("hard", answers(5, 0), "hard"),  # no higher level
        ("easy", answers(0, 5), "easy"),  # no lower level
    ],
)
def test_the_level_follows_recent_accuracy(level: str, since_last_move: list[Answer], expected: str):
    assert next_level(level, since_last_move) == expected


def test_weak_areas_need_attention_only_where_the_class_detects_them():
    weak = StudentMastery(attempts=6, accuracy=0.5, mastery=0.4)
    assert status(weak, ClassFeatures(weak_topic_detection=True)) == "needs_attention"
    assert status(weak, ClassFeatures()) == "learning"  # Nursery - Class 5: no "weak" label
    assert status(StudentMastery(attempts=4, accuracy=0.0, mastery=0.0), ClassFeatures()) == "learning"


def test_strong_needs_high_mastery_over_enough_answers():
    features = ClassFeatures(weak_topic_detection=True)
    assert status(StudentMastery(attempts=5, accuracy=1.0, mastery=0.9), features) == "strong"
    assert status(StudentMastery(attempts=4, accuracy=1.0, mastery=1.0), features) == "learning"
    assert status(StudentMastery(attempts=8, accuracy=0.8, mastery=0.7), features) == "learning"
