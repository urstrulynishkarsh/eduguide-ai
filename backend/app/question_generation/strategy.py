"""What to ask for: formats, difficulty mix and the goal strategy (docs/07 §7.10, spec §9)."""

from collections.abc import Sequence

from app.class_profiles import ClassProfile
from app.core.enums import Goal, QuestionFormat

# Class 9-12: the goal changes the mix of questions.
GOAL_STRATEGY: dict[Goal, str] = {
    Goal.JEE: "Prefer conceptual, numerical and application problems, often joining two concepts; "
    "lean towards medium and hard.",
    Goal.NEET: "Stay close to the NCERT text: conceptual MCQs, assertion-reason and application MCQs.",
    Goal.BOARD_EXAM: "Follow the board's question-paper pattern; include competency-based and "
    "case-based questions where they fit.",
    Goal.CUET: "Prefer MCQs that test understanding of the NCERT text.",
}

_DIFFICULTY = {
    "easy": "Every question is easy for this class.",
    "medium": "Every question is of medium difficulty for this class.",
    "hard": "Every question is hard for this class (still inside the class syllabus).",
    "mixed": "Mix the difficulty: about a third each of easy, medium and hard.",
}


def allowed_formats(profile: ClassProfile, question_type: str) -> list[QuestionFormat]:
    """The formats a session may use. A single format must be one the class allows."""
    if question_type == "mixed":
        return list(profile.question_formats)
    return [QuestionFormat(question_type)] if question_type in profile.question_formats else []


def task_lines(
    profile: ClassProfile,
    goal: str,
    difficulty: str,
    formats: list[QuestionFormat],
    mistakes: Sequence[str] = (),
) -> list[str]:
    lines = [
        _DIFFICULTY[difficulty],
        "Formats to use: " + ", ".join(formats) + ("." if len(formats) == 1 else " - use a variety."),
        "Styles you may use: " + ", ".join(profile.question_styles) + ".",
    ]
    if strategy := GOAL_STRATEGY.get(Goal(goal)):
        lines.append(strategy)
    if mistakes:
        lines.append(
            "This student keeps making these mistakes here: " + " | ".join(mistakes) + " Include questions "
            "that check them - where a format has options, one wrong option is the answer the mistake "
            "gives - and hints that address them."
        )
    return lines
