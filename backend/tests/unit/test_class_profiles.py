"""The class-aware rules. No database needed."""

import pytest

from app.class_profiles import all_class_profiles, check_learning_choices, get_class_profile, resolve_goal
from app.class_profiles.models import ConceptDepth, LanguageComplexity, QuestionComplexity, UIMode
from app.core.enums import ClassLevel, Goal, LearningBand, QuestionFormat, Stream


def test_every_class_from_nursery_to_12_has_a_profile():
    profiles = all_class_profiles()
    assert [profile.class_level for profile in profiles] == list(ClassLevel)
    assert len(profiles) == 15
    assert profiles[0].label == "Nursery"
    assert profiles[-1].label == "Class 12"


def test_class_5_matches_the_example_in_the_product_spec():
    profile = get_class_profile(ClassLevel.CLASS_5)
    assert profile.age_range == "9-11"
    assert profile.language_complexity == "simple"
    assert profile.question_complexity == "medium"
    assert profile.explanation_style == "child_friendly"
    assert profile.max_concept_depth == "intermediate"


def test_class_12_matches_the_example_in_the_product_spec():
    profile = get_class_profile("class_12")
    assert profile.age_range == "16-18"
    assert profile.language_complexity == "advanced"
    assert profile.question_complexity == "advanced"
    assert profile.explanation_style == "academic"
    assert profile.max_concept_depth == "advanced"


@pytest.mark.parametrize(
    ("class_level", "band"),
    [
        ("nursery", LearningBand.FOUNDATIONAL),
        ("ukg", LearningBand.FOUNDATIONAL),
        ("class_2", LearningBand.FOUNDATIONAL),
        ("class_3", LearningBand.PREPARATORY),
        ("class_5", LearningBand.PREPARATORY),
        ("class_6", LearningBand.MIDDLE),
        ("class_8", LearningBand.MIDDLE),
        ("class_9", LearningBand.SECONDARY),
        ("class_10", LearningBand.SECONDARY),
        ("class_11", LearningBand.SENIOR_SECONDARY),
        ("class_12", LearningBand.SENIOR_SECONDARY),
    ],
)
def test_classes_are_grouped_into_the_bands_of_the_spec(class_level, band):
    assert get_class_profile(class_level).band is band


@pytest.mark.parametrize(
    ("attribute", "scale"),
    [
        ("language_complexity", list(LanguageComplexity)),
        ("question_complexity", list(QuestionComplexity)),
        ("max_concept_depth", list(ConceptDepth)),
    ],
)
def test_difficulty_never_goes_down_as_the_class_goes_up(attribute, scale):
    positions = [scale.index(getattr(profile, attribute)) for profile in all_class_profiles()]
    assert positions == sorted(positions)


def test_number_limits_never_go_down_as_the_class_goes_up():
    for attribute in ("age_min", "max_sentence_words", "max_solution_steps", "max_session_questions"):
        values = [getattr(profile, attribute) for profile in all_class_profiles()]
        assert values == sorted(values), attribute


def test_nursery_to_class_2_is_visual_and_never_exam_style():
    for class_level in ("nursery", "lkg", "ukg", "class_1", "class_2"):
        profile = get_class_profile(class_level)
        assert profile.ui_mode is UIMode.PLAYFUL
        assert profile.mcq_option_count == 3
        assert set(profile.question_formats) == {
            QuestionFormat.VISUAL_CHOICE,
            QuestionFormat.MATCHING,
            QuestionFormat.COUNTING,
            QuestionFormat.MCQ,
        }
        assert not any(profile.features.model_dump().values()), "no exam features for early learners"


def test_exam_features_switch_on_at_the_classes_named_in_the_spec():
    assert get_class_profile("class_3").features.practice_tests
    assert not get_class_profile("class_5").features.adaptive_difficulty
    assert get_class_profile("class_6").features.adaptive_difficulty
    assert get_class_profile("class_6").features.weak_topic_detection
    assert not get_class_profile("class_8").features.timed_tests
    assert get_class_profile("class_9").features.timed_tests
    assert get_class_profile("class_9").features.previous_year_questions
    assert not get_class_profile("class_10").features.competitive_exam_modes
    assert get_class_profile("class_11").features.competitive_exam_modes
    assert get_class_profile("class_3").features.misconception_detection


def test_stream_and_competitive_goals_are_only_for_class_11_and_12():
    for profile in all_class_profiles():
        senior = profile.class_level in (ClassLevel.CLASS_11, ClassLevel.CLASS_12)
        assert profile.requires_stream is senior
        assert (Goal.JEE in profile.available_goals) is senior
        assert (profile.suggested_subjects_by_stream is not None) is senior
        assert profile.default_goal in profile.available_goals


def test_board_exam_years_default_to_the_board_exam_goal():
    assert resolve_goal(ClassLevel.CLASS_10, None) is Goal.BOARD_EXAM
    assert resolve_goal(ClassLevel.CLASS_12, None) is Goal.BOARD_EXAM
    assert resolve_goal(ClassLevel.CLASS_7, None) is Goal.SCHOOL_EXAM
    assert resolve_goal(ClassLevel.UKG, None) is Goal.GENERAL_LEARNING
    assert resolve_goal(ClassLevel.CLASS_12, Goal.JEE) is Goal.JEE


def test_a_valid_combination_has_no_problems():
    assert check_learning_choices(ClassLevel.CLASS_7, None, Goal.SCHOOL_EXAM) == []
    assert check_learning_choices(ClassLevel.CLASS_12, Stream.SCIENCE, Goal.JEE) == []
    assert check_learning_choices(ClassLevel.CLASS_11, Stream.ARTS, Goal.CUET) == []


@pytest.mark.parametrize(
    ("class_level", "stream", "goal", "field"),
    [
        (ClassLevel.CLASS_11, None, Goal.SCHOOL_EXAM, "stream"),  # stream missing
        (ClassLevel.CLASS_7, Stream.SCIENCE, Goal.SCHOOL_EXAM, "stream"),  # stream too early
        (ClassLevel.CLASS_7, None, Goal.JEE, "goal"),  # JEE too early
        (ClassLevel.NURSERY, None, Goal.BOARD_EXAM, "goal"),  # no exams in Nursery
        (ClassLevel.CLASS_12, Stream.COMMERCE, Goal.NEET, "goal"),  # NEET needs Science
        (ClassLevel.CLASS_12, Stream.ARTS, Goal.JEE, "goal"),  # JEE needs Science
    ],
)
def test_combinations_that_do_not_make_sense_are_reported(class_level, stream, goal, field):
    problems = check_learning_choices(class_level, stream, goal)
    assert [problem.field for problem in problems] == [field]
    assert problems[0].message


def test_class_level_helpers():
    assert ClassLevel.NURSERY.order == 0
    assert ClassLevel.CLASS_12.order == 14
    assert ClassLevel.LKG.grade is None
    assert ClassLevel.CLASS_9.grade == 9
    assert [level.label for level in list(ClassLevel)[:4]] == ["Nursery", "LKG", "UKG", "Class 1"]
