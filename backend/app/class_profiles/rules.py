"""Checks that a learner's choices make sense for their class."""

from dataclasses import dataclass

from app.class_profiles.registry import get_class_profile
from app.core.enums import ClassLevel, Goal, Stream


@dataclass(frozen=True, slots=True)
class FieldProblem:
    field: str
    message: str


def resolve_goal(class_level: ClassLevel, goal: Goal | None) -> Goal:
    """Use the class default when the parent did not pick a goal."""
    return goal if goal is not None else get_class_profile(class_level).default_goal


def check_learning_choices(class_level: ClassLevel, stream: Stream | None, goal: Goal) -> list[FieldProblem]:
    """Return every problem with the class / stream / goal combination. Empty means fine."""
    profile = get_class_profile(class_level)
    problems: list[FieldProblem] = []

    if profile.requires_stream and stream is None:
        problems.append(
            FieldProblem("stream", f"Please choose a stream (Science, Commerce or Arts) for {profile.label}.")
        )
    if not profile.requires_stream and stream is not None:
        problems.append(FieldProblem("stream", "A stream can only be chosen for Class 11 and Class 12."))

    if goal not in profile.available_goals:
        problems.append(FieldProblem("goal", f"This goal is not available for {profile.label}."))
    elif goal in (Goal.JEE, Goal.NEET) and stream is not None and stream is not Stream.SCIENCE:
        problems.append(FieldProblem("goal", "JEE and NEET preparation needs the Science stream."))

    return problems
