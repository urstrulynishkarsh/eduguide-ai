"""The hand-written demo questions must pass the same checks as questions the AI writes."""

import pytest

from app.class_profiles import get_class_profile
from app.core.enums import ClassLevel
from app.question_generation import validation
from scripts.demo_questions import CLASS_7_MATHS, UKG_PICTURES
from scripts.seed import SAMPLE_BOOKS, SAMPLE_DATA


@pytest.mark.parametrize(
    ("class_level", "questions"),
    [(ClassLevel.CLASS_7, CLASS_7_MATHS), (ClassLevel.UKG, UKG_PICTURES)],
)
def test_demo_questions_pass_the_program_checks(class_level, questions):
    profile = get_class_profile(class_level)
    seen: set[str] = set()
    for _, question in questions:
        problem = validation.problems(
            question,
            profile=profile,
            formats=list(profile.question_formats),
            difficulty="mixed",
            tags={"S1"},
            seen=seen,
        )
        assert problem is None, f"{question.text!r}: {problem}"
        seen.add(validation.normalize(question.text))


def test_demo_questions_name_exercises_that_are_in_their_book():
    for _, _, _, file_name, questions in SAMPLE_BOOKS:
        text = (SAMPLE_DATA / file_name).read_text()
        for exercise_label, _ in questions:
            assert exercise_label is None or exercise_label in text
