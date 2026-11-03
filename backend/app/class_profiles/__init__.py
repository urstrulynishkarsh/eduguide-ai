"""Class-aware learning rules.

There is one `ClassProfile` for every class from Nursery to Class 12. Anything
that must behave differently by age reads its rules from here: the child
profile form today; question generation, explanations, hints, tests and the
UI in later steps. Described for people in docs/07-class-aware-rules.md.
"""

from app.class_profiles.models import ClassFeatures, ClassProfile, UIMode
from app.class_profiles.registry import CLASS_PROFILES, all_class_profiles, get_class_profile
from app.class_profiles.rules import FieldProblem, check_learning_choices, resolve_goal

__all__ = [
    "CLASS_PROFILES",
    "ClassFeatures",
    "ClassProfile",
    "FieldProblem",
    "UIMode",
    "all_class_profiles",
    "check_learning_choices",
    "get_class_profile",
    "resolve_goal",
]
