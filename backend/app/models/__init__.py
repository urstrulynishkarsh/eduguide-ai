"""Database tables.

Import every model here so that `Base.metadata` (used by migrations and tests)
always knows about all tables.
"""

from app.models.base import Base
from app.models.library import Book, Chapter, Document, DocumentChunk, Exercise, Topic
from app.models.student import Student, StudentProfile
from app.models.user import Parent, User

__all__ = [
    "Base",
    "Book",
    "Chapter",
    "Document",
    "DocumentChunk",
    "Exercise",
    "Parent",
    "Student",
    "StudentProfile",
    "Topic",
    "User",
]
