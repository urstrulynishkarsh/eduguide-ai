"""Database tables.

Import every model here so that `Base.metadata` (used by migrations and tests)
always knows about all tables.
"""

from app.models.adaptive import Recommendation, StudentMastery, StudentMisconception
from app.models.base import Base
from app.models.chat import ChatMessage, ChatSession
from app.models.library import Book, Chapter, Document, DocumentChunk, Exercise, Topic
from app.models.mock_test import MockTest, MockTestAttempt, MockTestQuestion
from app.models.paper import PaperAnalysis, PaperQuestion
from app.models.practice import PracticeItem, PracticeSession, Question, QuestionAttempt
from app.models.student import Student, StudentProfile
from app.models.study_plan import StudyPlan, StudyPlanItem
from app.models.user import Parent, User

__all__ = [
    "Base",
    "Book",
    "Chapter",
    "ChatMessage",
    "ChatSession",
    "Document",
    "DocumentChunk",
    "Exercise",
    "MockTest",
    "MockTestAttempt",
    "MockTestQuestion",
    "PaperAnalysis",
    "PaperQuestion",
    "Parent",
    "PracticeItem",
    "PracticeSession",
    "Question",
    "QuestionAttempt",
    "Recommendation",
    "Student",
    "StudentMastery",
    "StudentMisconception",
    "StudentProfile",
    "StudyPlan",
    "StudyPlanItem",
    "Topic",
    "User",
]
