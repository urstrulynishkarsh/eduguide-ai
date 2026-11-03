"""Every generated question is checked before use (spec §19), and answers are marked exactly."""

import pytest

from app.class_profiles import get_class_profile
from app.core.enums import ClassLevel, QuestionFormat
from app.models import Question
from app.question_generation import checking, validation
from app.question_generation.schemas import Grade, Review
from tests.fakes import make_question

CLASS_8 = get_class_profile(ClassLevel.CLASS_8)
UKG = get_class_profile(ClassLevel.UKG)
ALL_FORMATS = list(QuestionFormat)


def _problems(question, profile=CLASS_8, *, formats=ALL_FORMATS, difficulty="mixed", seen=frozenset()):
    return validation.problems(
        question, profile=profile, formats=formats, difficulty=difficulty, tags={"S1", "S2"}, seen=set(seen)
    )


def test_a_good_question_passes():
    assert _problems(make_question()) is None


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"options": ["1", "2", "3"]}, "exactly 4"),
        ({"options": ["1", "2", "2", "4"]}, "exactly 4"),
        ({"correct_option": 4}, "correct_option"),
        ({"correct_option": None}, "correct_option"),
        ({"source_tags": ["S9"]}, "source_tags"),
        ({"source_tags": []}, "source_tags"),
        ({"style": "competitive_exam"}, "style"),
        ({"steps": [f"step {n}" for n in range(7)]}, "1 to 6 steps"),
        ({"hints": []}, "hints"),
        ({"text": " ".join(["word"] * 40) + "?"}, "near 20 words"),
        ({"format": "case_based", "case": None}, "case"),
        ({"format": "fill_blank", "options": [], "correct_option": None, "accepted_answers": ["3"]}, "____"),
        ({"format": "numerical", "options": [], "correct_option": None}, "numeric_answer"),
        (
            {"format": "short_answer", "options": [], "correct_option": None, "model_answer": "x = 3"},
            "key_points",
        ),
        (
            {
                "format": "matching",
                "options": [],
                "correct_option": None,
                "match_left": ["a"],
                "match_right": ["b"],
            },
            "2 to 5 pairs",
        ),
    ],
)
def test_broken_questions_are_rejected_with_a_reason(overrides, reason):
    assert reason in (_problems(make_question(**overrides)) or "")


def test_format_difficulty_and_repeats_are_checked():
    question = make_question()
    assert "not asked for" in _problems(question, formats=[QuestionFormat.SHORT_ANSWER])
    assert "difficulty" in _problems(question, difficulty="hard")
    assert "repeats" in _problems(question, seen={validation.normalize("What is X, if 2x + 4 = 10")})


def test_the_youngest_get_three_picture_options():
    picture = make_question(
        format="visual_choice",
        text="Which one is an apple?",
        options=["🍎 Apple", "🐱 Cat", "🚗 Car"],
        correct_option=0,
        steps=["It is red and round."],
        hints=["You can eat it."],
    )
    assert _problems(picture, UKG) is None
    no_pictures = picture.model_copy(update={"options": ["Apple", "Cat", "Car"]})
    assert "emoji" in _problems(no_pictures, UKG)
    # A four-option MCQ is too many choices for UKG, which uses three.
    assert "exactly 3" in _problems(make_question(), UKG, formats=list(UKG.question_formats))


def _review(**overrides) -> Review:
    values = {
        "number": 1,
        "solved_option": 2,
        "solved_value": None,
        "solved_text": None,
        "shown_answer_correct": None,
        "supported_by_passages": True,
        "fits_class": True,
        "difficulty": "medium",
        "problem": "",
    }
    return Review(**{**values, **overrides})


def test_the_independent_review_must_agree():
    question = make_question()
    assert validation.review_problem(question, _review(), difficulty="medium") is None
    assert "different option" in validation.review_problem(
        question, _review(solved_option=1), difficulty="mixed"
    )
    assert "passages" in validation.review_problem(
        question, _review(supported_by_passages=False), difficulty="mixed"
    )
    assert "beyond" in validation.review_problem(
        question, _review(fits_class=False, problem="uses ideas beyond Class 8"), difficulty="mixed"
    )
    hard = make_question(difficulty="hard")
    assert "judged easy" in validation.review_problem(hard, _review(difficulty="easy"), difficulty="hard")
    assert validation.review_problem(hard, _review(difficulty="medium"), difficulty="hard") is None

    numerical = make_question(format="numerical", options=[], correct_option=None, numeric_answer=3.0)
    assert (
        validation.review_problem(
            numerical, _review(solved_option=None, solved_value=3.001), difficulty="mixed"
        )
        is None
    )
    assert "different number" in validation.review_problem(
        numerical, _review(solved_option=None, solved_value=4.0), difficulty="mixed"
    )


def _stored(fmt: str, answer: dict) -> Question:
    return Question(format=fmt, answer=answer, body={"text": "q"})


def test_answers_are_marked_exactly():
    assert checking.is_correct(_stored("mcq", {"option": 2}), {"option": 2})
    assert not checking.is_correct(_stored("mcq", {"option": 2}), {"option": 1})
    assert checking.is_correct(_stored("numerical", {"value": 9.8}), {"value": 9.80001})
    assert checking.is_correct(_stored("counting", {"value": 5}), {"value": 5})
    assert checking.is_correct(
        _stored("fill_blank", {"accepted": ["equation", "an equation"]}), {"text": " Equation. "}
    )
    assert checking.is_correct(_stored("fill_blank", {"accepted": ["समीकरण"]}), {"text": "समीकरण"})
    assert checking.is_correct(_stored("matching", {"pairs": [2, 0, 1]}), {"pairs": [2, 0, 1]})
    assert not checking.is_correct(_stored("matching", {"pairs": [2, 0, 1]}), {"pairs": [0, 1, 2]})


def test_an_answer_of_the_wrong_shape_is_refused():
    with pytest.raises(checking.AnswerShapeError):
        checking.is_correct(_stored("mcq", {"option": 2}), {"text": "two"})
    with pytest.raises(checking.AnswerShapeError):
        checking.is_correct(_stored("short_answer", {"model_answer": "x"}), {"option": 1})


def test_written_answers_are_left_to_the_tutor_and_earn_part_marks():
    question = _stored("long_answer", {"model_answer": "x", "key_points": ["a", "b", "c"]})
    assert checking.is_correct(question, {"text": "an answer"}) is None
    grade = Grade(is_correct=False, key_points_covered=2, feedback="Add the third point.")
    assert checking.written_marks(question, grade, 5) == 3.5  # 2 of 3 points of 5 marks, to half a mark
    assert checking.written_marks(question, grade.model_copy(update={"key_points_covered": 9}), 5) == 5
