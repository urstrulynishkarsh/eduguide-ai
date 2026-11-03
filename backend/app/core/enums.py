"""Shared vocabulary of the product.

These values are stored in the database and sent over the API exactly as
written here (lower-case text), so treat them as a contract: add new values
freely, but never rename an existing one without a data migration.
"""

from enum import StrEnum


class Role(StrEnum):
    PARENT = "parent"
    STUDENT = "student"


class ClassLevel(StrEnum):
    """Every class the platform supports, in school order."""

    NURSERY = "nursery"
    LKG = "lkg"
    UKG = "ukg"
    CLASS_1 = "class_1"
    CLASS_2 = "class_2"
    CLASS_3 = "class_3"
    CLASS_4 = "class_4"
    CLASS_5 = "class_5"
    CLASS_6 = "class_6"
    CLASS_7 = "class_7"
    CLASS_8 = "class_8"
    CLASS_9 = "class_9"
    CLASS_10 = "class_10"
    CLASS_11 = "class_11"
    CLASS_12 = "class_12"

    @property
    def order(self) -> int:
        """Position in school order: Nursery = 0 ... Class 12 = 14."""
        return list(ClassLevel).index(self)

    @property
    def grade(self) -> int | None:
        """The class number (1-12), or None for Nursery / LKG / UKG."""
        return int(self.value.removeprefix("class_")) if self.value.startswith("class_") else None

    @property
    def label(self) -> str:
        """Name shown to people: "Nursery", "LKG", "Class 7"."""
        if self.grade is not None:
            return f"Class {self.grade}"
        return "Nursery" if self is ClassLevel.NURSERY else self.value.upper()


class LearningBand(StrEnum):
    """Groups of classes that share one learning experience.

    The grouping follows the product spec (and happens to match the stages of
    India's NEP 2020, with the secondary stage split in two).
    """

    FOUNDATIONAL = "foundational"  # Nursery - Class 2
    PREPARATORY = "preparatory"  # Class 3 - 5
    MIDDLE = "middle"  # Class 6 - 8
    SECONDARY = "secondary"  # Class 9 - 10
    SENIOR_SECONDARY = "senior_secondary"  # Class 11 - 12


class Board(StrEnum):
    CBSE = "cbse"
    ICSE = "icse"
    STATE = "state"
    OTHER = "other"


class Stream(StrEnum):
    """Only for Class 11 and 12."""

    SCIENCE = "science"
    COMMERCE = "commerce"
    ARTS = "arts"


class Goal(StrEnum):
    """What the learner is preparing for. Changes how questions are generated."""

    GENERAL_LEARNING = "general_learning"
    SCHOOL_EXAM = "school_exam"
    BOARD_EXAM = "board_exam"
    JEE = "jee"
    NEET = "neet"
    CUET = "cuet"
    OTHER = "other"


class QuestionFormat(StrEnum):
    """How a question is shown and answered."""

    VISUAL_CHOICE = "visual_choice"  # "Which one is an apple?" with pictures
    MATCHING = "matching"
    COUNTING = "counting"
    MCQ = "mcq"
    FILL_BLANK = "fill_blank"
    TRUE_FALSE = "true_false"
    SHORT_ANSWER = "short_answer"
    LONG_ANSWER = "long_answer"
    NUMERICAL = "numerical"
    ASSERTION_REASON = "assertion_reason"
    CASE_BASED = "case_based"


class QuestionStyle(StrEnum):
    """What kind of thinking a question asks for. Any style can use any format."""

    RECALL = "recall"
    CONCEPTUAL = "conceptual"
    WORD_PROBLEM = "word_problem"
    APPLICATION = "application"
    HOTS = "hots"
    COMPETENCY_BASED = "competency_based"
    BOARD_STYLE = "board_style"
    COMPETITIVE_EXAM = "competitive_exam"


class MaterialType(StrEnum):
    """What kind of material a book in "My Books" is (spec §13)."""

    TEXTBOOK = "textbook"
    NOTES = "notes"
    QUESTION_BANK = "question_bank"
    PREVIOUS_YEAR_PAPER = "previous_year_paper"
    ASSIGNMENT = "assignment"
    STUDY_MATERIAL = "study_material"


class FileKind(StrEnum):
    """File types that can be uploaded. Decided from the file's content, never from its name."""

    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"


class DocumentStatus(StrEnum):
    QUEUED = "queued"  # uploaded, waiting for its turn
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class ProcessingStage(StrEnum):
    """Steps of reading a book, in order. The frontend shows them as a checklist in parent words
    (docs/04-frontend-routes.md): Reading your book · Finding the chapters · Finding exercises and
    questions · Understanding the topics · Getting practice ready."""

    EXTRACT_TEXT = "extract_text"
    DETECT_CHAPTERS = "detect_chapters"
    DETECT_EXERCISES = "detect_exercises"
    DETECT_TOPICS = "detect_topics"
    MAKE_CHUNKS = "make_chunks"


class ContentType(StrEnum):
    """What a piece of book text is. One exercise question or one worked example is one piece."""

    CONCEPT = "concept"
    EXAMPLE = "example"
    EXERCISE_QUESTION = "exercise_question"
    SUMMARY = "summary"
    OTHER = "other"  # contents page, foreword, answer keys...


# Labels shown in forms. The frontend translates them; these are the English defaults.
BOARD_LABELS: dict[Board, str] = {
    Board.CBSE: "CBSE",
    Board.ICSE: "ICSE / ISC",
    Board.STATE: "State Board",
    Board.OTHER: "Other",
}

STREAM_LABELS: dict[Stream, str] = {
    Stream.SCIENCE: "Science",
    Stream.COMMERCE: "Commerce",
    Stream.ARTS: "Arts / Humanities",
}

GOAL_LABELS: dict[Goal, str] = {
    Goal.GENERAL_LEARNING: "Build strong basics",
    Goal.SCHOOL_EXAM: "School exams",
    Goal.BOARD_EXAM: "Board exams",
    Goal.JEE: "JEE",
    Goal.NEET: "NEET",
    Goal.CUET: "CUET",
    Goal.OTHER: "Other",
}

MATERIAL_TYPE_LABELS: dict[MaterialType, str] = {
    MaterialType.TEXTBOOK: "Textbook",
    MaterialType.NOTES: "School notes",
    MaterialType.QUESTION_BANK: "Question bank",
    MaterialType.PREVIOUS_YEAR_PAPER: "Previous-year papers",
    MaterialType.ASSIGNMENT: "Assignment",
    MaterialType.STUDY_MATERIAL: "Study material",
}
