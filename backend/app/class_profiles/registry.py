"""The class profiles themselves.

Classes that share an experience are described once as a group, then expanded
into one `ClassProfile` per class. To change how the platform treats a class,
edit the group here - nothing else needs to change.

The number limits (sentence length, steps, session size) are sensible starting
values, not research findings. Tune them after watching real children use it.
"""

from typing import Any

from app.class_profiles.models import (
    ClassFeatures,
    ClassProfile,
    ConceptDepth,
    ExplanationStyle,
    LanguageComplexity,
    QuestionComplexity,
    UIMode,
)
from app.core.enums import ClassLevel as C
from app.core.enums import Goal, LearningBand, Stream
from app.core.enums import QuestionFormat as F
from app.core.enums import QuestionStyle as S

_STAY_IN_CLASS = "Stay inside the chapter and the class syllabus. Do not bring in ideas from higher classes."

_GROUPS: tuple[dict[str, Any], ...] = (
    # ------------------------------------------------------------------ Nursery, LKG, UKG
    {
        "levels": (C.NURSERY, C.LKG, C.UKG),
        "band": LearningBand.FOUNDATIONAL,
        "language_complexity": LanguageComplexity.VERY_SIMPLE,
        "question_complexity": QuestionComplexity.VERY_EASY,
        "explanation_style": ExplanationStyle.PLAYFUL,
        "max_concept_depth": ConceptDepth.INTRODUCTORY,
        "max_sentence_words": 8,
        "max_solution_steps": 1,
        "mcq_option_count": 3,
        "default_session_questions": 5,
        "max_session_questions": 10,
        "question_formats": (F.VISUAL_CHOICE, F.MATCHING, F.COUNTING, F.MCQ),
        "question_styles": (S.RECALL,),
        "requires_stream": False,
        "available_goals": (Goal.GENERAL_LEARNING, Goal.OTHER),
        "default_goal": Goal.GENERAL_LEARNING,
        "suggested_subjects": ("English", "Hindi", "Maths", "General Awareness"),
        "ui_mode": UIMode.PLAYFUL,
        "features": ClassFeatures(),
        "ai_guidelines": (
            "Talk like a warm, patient pre-school teacher.",
            "Use very short sentences and words a small child hears at home.",
            "Ask about one thing at a time: a colour, a shape, a letter, a number or an everyday object.",
            "Prefer pictures or emoji, counting, matching and 'which one is...' questions.",
            "Always encourage. Never say 'wrong' or 'incorrect'; invite the child to try again.",
            "No marks, no timers and no exam words.",
        ),
    },
    # ------------------------------------------------------------------ Class 1 - 2
    {
        "levels": (C.CLASS_1, C.CLASS_2),
        "band": LearningBand.FOUNDATIONAL,
        "language_complexity": LanguageComplexity.SIMPLE,
        "question_complexity": QuestionComplexity.EASY,
        "explanation_style": ExplanationStyle.PLAYFUL,
        "max_concept_depth": ConceptDepth.BASIC,
        "max_sentence_words": 10,
        "max_solution_steps": 2,
        "mcq_option_count": 3,
        "default_session_questions": 5,
        "max_session_questions": 10,
        "question_formats": (F.VISUAL_CHOICE, F.MATCHING, F.COUNTING, F.MCQ),
        "question_styles": (S.RECALL,),
        "requires_stream": False,
        "available_goals": (Goal.GENERAL_LEARNING, Goal.SCHOOL_EXAM, Goal.OTHER),
        "default_goal": Goal.GENERAL_LEARNING,
        "suggested_subjects": ("English", "Hindi", "Mathematics", "EVS"),
        "ui_mode": UIMode.PLAYFUL,
        "features": ClassFeatures(),
        "ai_guidelines": (
            "Talk like a friendly primary-school teacher.",
            "Use short sentences and simple everyday words.",
            "One idea per question: simple reading, basic vocabulary or basic arithmetic.",
            "Use familiar things in examples: fruits, toys, animals, family, school.",
            "Always encourage. Never say 'wrong'; invite the child to try again.",
            "No exam-style language.",
        ),
    },
    # ------------------------------------------------------------------ Class 3 - 5
    {
        "levels": (C.CLASS_3, C.CLASS_4, C.CLASS_5),
        "band": LearningBand.PREPARATORY,
        "language_complexity": LanguageComplexity.SIMPLE,
        "question_complexity": QuestionComplexity.MEDIUM,
        "explanation_style": ExplanationStyle.CHILD_FRIENDLY,
        "max_concept_depth": ConceptDepth.INTERMEDIATE,
        "max_sentence_words": 15,
        "max_solution_steps": 4,
        "mcq_option_count": 4,
        "default_session_questions": 8,
        "max_session_questions": 20,
        "question_formats": (F.MCQ, F.FILL_BLANK, F.TRUE_FALSE, F.SHORT_ANSWER),
        "question_styles": (S.RECALL, S.CONCEPTUAL, S.WORD_PROBLEM, S.HOTS),
        "requires_stream": False,
        "available_goals": (Goal.SCHOOL_EXAM, Goal.GENERAL_LEARNING, Goal.OTHER),
        "default_goal": Goal.SCHOOL_EXAM,
        "suggested_subjects": ("English", "Hindi", "Mathematics", "EVS", "Computer"),
        "ui_mode": UIMode.FRIENDLY,
        "features": ClassFeatures(exam_style_practice=True, practice_tests=True),
        "ai_guidelines": (
            "Explain with simple examples from daily life: money, sweets, cricket, school, family.",
            "Break every explanation into small numbered steps.",
            "When you use a new word, say what it means in plain language.",
            "Keep word problems to one or two operations.",
            "Keep thinking (HOTS) questions gentle: one small twist on what the chapter teaches.",
            "Be encouraging and praise effort.",
            _STAY_IN_CLASS,
        ),
    },
    # ------------------------------------------------------------------ Class 6 - 8
    {
        "levels": (C.CLASS_6, C.CLASS_7, C.CLASS_8),
        "band": LearningBand.MIDDLE,
        "language_complexity": LanguageComplexity.MODERATE,
        "question_complexity": QuestionComplexity.UPPER_MEDIUM,
        "explanation_style": ExplanationStyle.CONCEPTUAL,
        "max_concept_depth": ConceptDepth.UPPER_INTERMEDIATE,
        "max_sentence_words": 20,
        "max_solution_steps": 6,
        "mcq_option_count": 4,
        "default_session_questions": 10,
        "max_session_questions": 30,
        "question_formats": (F.MCQ, F.SHORT_ANSWER, F.LONG_ANSWER, F.CASE_BASED, F.ASSERTION_REASON),
        "question_styles": (S.RECALL, S.CONCEPTUAL, S.WORD_PROBLEM, S.APPLICATION, S.HOTS),
        "requires_stream": False,
        "available_goals": (Goal.SCHOOL_EXAM, Goal.GENERAL_LEARNING, Goal.OTHER),
        "default_goal": Goal.SCHOOL_EXAM,
        "suggested_subjects": (
            "Mathematics",
            "Science",
            "Social Science",
            "English",
            "Hindi",
            "Sanskrit",
            "Computer",
        ),
        "ui_mode": UIMode.STANDARD,
        "features": ClassFeatures(
            exam_style_practice=True,
            practice_tests=True,
            chapter_tests=True,
            adaptive_difficulty=True,
            weak_topic_detection=True,
        ),
        "ai_guidelines": (
            "Explain why a rule works, not only how to apply it.",
            "Use the correct subject terms and define each one the first time it appears.",
            "Connect ideas to real situations; include application and thinking (HOTS) questions.",
            "Use assertion-reason and case-based questions only where they fit the chapter.",
            "Point out the common mistake for a concept when it helps.",
            _STAY_IN_CLASS,
        ),
    },
    # ------------------------------------------------------------------ Class 9 - 10
    {
        "levels": (C.CLASS_9, C.CLASS_10),
        "band": LearningBand.SECONDARY,
        "language_complexity": LanguageComplexity.STANDARD,
        "question_complexity": QuestionComplexity.CHALLENGING,
        "explanation_style": ExplanationStyle.EXAM_ORIENTED,
        "max_concept_depth": ConceptDepth.PROFICIENT,
        "max_sentence_words": 25,
        "max_solution_steps": 8,
        "mcq_option_count": 4,
        "default_session_questions": 10,
        "max_session_questions": 50,
        "question_formats": (
            F.MCQ,
            F.SHORT_ANSWER,
            F.LONG_ANSWER,
            F.NUMERICAL,
            F.ASSERTION_REASON,
            F.CASE_BASED,
        ),
        "question_styles": (
            S.RECALL,
            S.CONCEPTUAL,
            S.APPLICATION,
            S.HOTS,
            S.COMPETENCY_BASED,
            S.BOARD_STYLE,
        ),
        "requires_stream": False,
        "available_goals": (Goal.SCHOOL_EXAM, Goal.BOARD_EXAM, Goal.GENERAL_LEARNING, Goal.OTHER),
        "default_goal": Goal.SCHOOL_EXAM,
        "suggested_subjects": (
            "Mathematics",
            "Science",
            "Social Science",
            "English",
            "Hindi",
            "Sanskrit",
            "Information Technology",
        ),
        "ui_mode": UIMode.DENSE,
        "features": ClassFeatures(
            exam_style_practice=True,
            practice_tests=True,
            chapter_tests=True,
            adaptive_difficulty=True,
            weak_topic_detection=True,
            timed_tests=True,
            full_mock_tests=True,
            previous_year_questions=True,
            board_exam_preparation=True,
        ),
        "ai_guidelines": (
            "Follow the question style and marking pattern of the learner's board.",
            "Use textbook terminology exactly and show the working a board examiner expects.",
            "Include competency-based, case-study and assertion-reason questions where they fit the chapter.",
            "Mention common exam mistakes and where marks are usually lost.",
            _STAY_IN_CLASS,
        ),
    },
    # ------------------------------------------------------------------ Class 11 - 12
    {
        "levels": (C.CLASS_11, C.CLASS_12),
        "band": LearningBand.SENIOR_SECONDARY,
        "language_complexity": LanguageComplexity.ADVANCED,
        "question_complexity": QuestionComplexity.ADVANCED,
        "explanation_style": ExplanationStyle.ACADEMIC,
        "max_concept_depth": ConceptDepth.ADVANCED,
        "max_sentence_words": 30,
        "max_solution_steps": 12,
        "mcq_option_count": 4,
        "default_session_questions": 10,
        "max_session_questions": 50,
        "question_formats": (
            F.MCQ,
            F.SHORT_ANSWER,
            F.LONG_ANSWER,
            F.NUMERICAL,
            F.ASSERTION_REASON,
            F.CASE_BASED,
        ),
        "question_styles": (
            S.RECALL,
            S.CONCEPTUAL,
            S.APPLICATION,
            S.HOTS,
            S.COMPETENCY_BASED,
            S.BOARD_STYLE,
            S.COMPETITIVE_EXAM,
        ),
        "requires_stream": True,
        "available_goals": (Goal.SCHOOL_EXAM, Goal.BOARD_EXAM, Goal.JEE, Goal.NEET, Goal.CUET, Goal.OTHER),
        "default_goal": Goal.SCHOOL_EXAM,
        "suggested_subjects": ("English",),
        "suggested_subjects_by_stream": {
            Stream.SCIENCE: (
                "Physics",
                "Chemistry",
                "Mathematics",
                "Biology",
                "English",
                "Computer Science",
            ),
            Stream.COMMERCE: (
                "Accountancy",
                "Business Studies",
                "Economics",
                "Mathematics",
                "English",
            ),
            Stream.ARTS: (
                "History",
                "Political Science",
                "Geography",
                "Economics",
                "Sociology",
                "Psychology",
                "English",
            ),
        },
        "ui_mode": UIMode.DENSE,
        "features": ClassFeatures(
            exam_style_practice=True,
            practice_tests=True,
            chapter_tests=True,
            adaptive_difficulty=True,
            weak_topic_detection=True,
            timed_tests=True,
            full_mock_tests=True,
            previous_year_questions=True,
            board_exam_preparation=True,
            competitive_exam_modes=True,
        ),
        "ai_guidelines": (
            "Be rigorous: precise definitions, standard notation, SI units and justified steps.",
            "Match the question style to the learner's goal: school exam, board exam, JEE, NEET or CUET.",
            "For a JEE goal prefer conceptual, numerical and multi-concept problems at higher difficulty.",
            "For a NEET goal stay close to the NCERT text: conceptual, assertion-reason, application MCQs.",
            "Derive or justify results wherever the syllabus expects it.",
            "Stay inside the Class 11-12 syllabus unless the learner asks to go further.",
        ),
    },
)

# Typical ages. Class 1-12 follow one pattern (Class 5 -> 9-11, Class 12 -> 16-18).
_PRE_PRIMARY_AGES: dict[C, tuple[int, int]] = {C.NURSERY: (3, 4), C.LKG: (4, 5), C.UKG: (5, 6)}

# The years that end in a board exam prepare for it by default.
_DEFAULT_GOAL_OVERRIDES: dict[C, Goal] = {C.CLASS_10: Goal.BOARD_EXAM, C.CLASS_12: Goal.BOARD_EXAM}


def _ages(level: C) -> tuple[int, int]:
    if level.grade is None:
        return _PRE_PRIMARY_AGES[level]
    return level.grade + 4, level.grade + 6


def _build() -> dict[C, ClassProfile]:
    profiles: dict[C, ClassProfile] = {}
    for group in _GROUPS:
        shared = {key: value for key, value in group.items() if key != "levels"}
        for level in group["levels"]:
            age_min, age_max = _ages(level)
            values = {
                **shared,
                "class_level": level,
                "label": level.label,
                "age_min": age_min,
                "age_max": age_max,
            }
            if level in _DEFAULT_GOAL_OVERRIDES:
                values["default_goal"] = _DEFAULT_GOAL_OVERRIDES[level]
            profiles[level] = ClassProfile(**values)

    missing = [level.value for level in C if level not in profiles]
    if missing:  # fail at start-up, not in front of a child
        raise RuntimeError(f"No class profile defined for: {', '.join(missing)}")
    return profiles


CLASS_PROFILES: dict[C, ClassProfile] = _build()


def get_class_profile(class_level: C | str) -> ClassProfile:
    return CLASS_PROFILES[C(class_level)]


def all_class_profiles() -> list[ClassProfile]:
    """Every profile in school order, Nursery first."""
    return [CLASS_PROFILES[level] for level in C]
