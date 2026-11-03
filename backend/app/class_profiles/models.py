"""The shape of a class profile."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, computed_field

from app.core.enums import ClassLevel, Goal, LearningBand, QuestionFormat, QuestionStyle, Stream


class LanguageComplexity(StrEnum):
    VERY_SIMPLE = "very_simple"
    SIMPLE = "simple"
    MODERATE = "moderate"
    STANDARD = "standard"
    ADVANCED = "advanced"


class QuestionComplexity(StrEnum):
    VERY_EASY = "very_easy"
    EASY = "easy"
    MEDIUM = "medium"
    UPPER_MEDIUM = "upper_medium"
    CHALLENGING = "challenging"
    ADVANCED = "advanced"


class ExplanationStyle(StrEnum):
    PLAYFUL = "playful"
    CHILD_FRIENDLY = "child_friendly"
    CONCEPTUAL = "conceptual"
    EXAM_ORIENTED = "exam_oriented"
    ACADEMIC = "academic"


class ConceptDepth(StrEnum):
    INTRODUCTORY = "introductory"
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    UPPER_INTERMEDIATE = "upper_intermediate"
    PROFICIENT = "proficient"
    ADVANCED = "advanced"


class UIMode(StrEnum):
    """How dense the screens are. The frontend picks its layout from this."""

    PLAYFUL = "playful"  # large cards and buttons, pictures, very little text
    FRIENDLY = "friendly"  # roomy, colourful, simple words
    STANDARD = "standard"  # regular app layout
    DENSE = "dense"  # academic dashboard: charts, tables, exam focus


class ClassFeatures(BaseModel):
    """What the product offers at this class. The UI hides whatever is off."""

    model_config = ConfigDict(frozen=True)

    exam_style_practice: bool = False  # marks, sections, formal question papers
    practice_tests: bool = False  # short untimed tests
    chapter_tests: bool = False
    adaptive_difficulty: bool = False
    weak_topic_detection: bool = False
    timed_tests: bool = False
    full_mock_tests: bool = False
    previous_year_questions: bool = False
    board_exam_preparation: bool = False
    competitive_exam_modes: bool = False  # JEE / NEET / CUET


class ClassProfile(BaseModel):
    """Everything that changes with the learner's class.

    The AI reads this when it writes questions, solutions, explanations, hints,
    study plans, mock tests and recommendations. The frontend reads it to pick
    the right layout and to hide features that do not fit the age group.
    """

    model_config = ConfigDict(frozen=True)

    class_level: ClassLevel
    label: str
    band: LearningBand
    age_min: int
    age_max: int

    # The descriptive scales named in the product spec.
    language_complexity: LanguageComplexity
    question_complexity: QuestionComplexity
    explanation_style: ExplanationStyle
    max_concept_depth: ConceptDepth

    # The same idea as numbers a validator can check.
    max_sentence_words: int
    max_solution_steps: int
    mcq_option_count: int
    default_session_questions: int
    max_session_questions: int

    # What kinds of questions may be generated.
    question_formats: tuple[QuestionFormat, ...]
    question_styles: tuple[QuestionStyle, ...]

    # Rules for the child profile form.
    requires_stream: bool
    available_goals: tuple[Goal, ...]
    default_goal: Goal
    suggested_subjects: tuple[str, ...]
    suggested_subjects_by_stream: dict[Stream, tuple[str, ...]] | None = None

    # The experience.
    ui_mode: UIMode
    features: ClassFeatures
    ai_guidelines: tuple[str, ...]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def age_range(self) -> str:
        return f"{self.age_min}-{self.age_max}"
