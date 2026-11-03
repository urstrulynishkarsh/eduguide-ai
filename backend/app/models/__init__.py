"""Database tables.

Import every model here so that `Base.metadata` (used by migrations and tests)
always knows about all tables.
"""

from app.models.adaptive import Recommendation, StudentMastery
from app.models.base import Base
from app.models.library import Book, Chapter, Document, DocumentChunk, Exercise, Topic
from app.models.mock_test import MockTest, MockTestAttempt, MockTestQuestion
from app.models.practice import PracticeItem, PracticeSession, Question, QuestionAttempt
from app.models.student import Student, StudentProfile
from app.models.study_plan import StudyPlan, StudyPlanItem
from app.models.user import Parent, User

__all__ = [
    "Base",
    "Book",
    "Chapter",
    "Document",
    "DocumentChunk",
    "Exercise",
    "MockTest",
    "MockTestAttempt",
    "MockTestQuestion",
    "Parent",
    "PracticeItem",
    "PracticeSession",
    "Question",
    "QuestionAttempt",
    "Recommendation",
    "Student",
    "StudentMastery",
    "StudentProfile",
    "StudyPlan",
    "StudyPlanItem",
    "Topic",
    "User",
]
