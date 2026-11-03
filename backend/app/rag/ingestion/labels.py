"""The one-line label placed in front of every chunk, e.g.

    Class 8 · Mathematics · Chapter 2 Linear Equations · 2.3 Solving Equations · Exercise 2.3 · Question 4

It makes short pieces (a bare equation) findable and tells the AI where a passage comes from.
Built while reading a book, and rebuilt when a parent renames a chapter or changes the book's class.
"""

from collections.abc import Mapping
from typing import Protocol

from app.core.enums import ClassLevel, ContentType

SEPARATOR = " · "
MAX_LENGTH = 400


def chapter_label(number: int | None, title: str) -> str:
    """'Chapter 2 Linear Equations', without repeating 'Chapter 2' when the title already says it."""
    if number is None or title.casefold().startswith(("chapter", "अध्याय")):
        return title
    return f"Chapter {number} {title}"


# Both what the reader found (structure.Detected*) and the stored rows (models.Chapter...) fit these.
class ChapterLike(Protocol):
    @property
    def number(self) -> int | None: ...
    @property
    def title(self) -> str: ...


class TopicLike(Protocol):
    @property
    def number(self) -> str | None: ...
    @property
    def title(self) -> str: ...


class ExerciseLike(Protocol):
    @property
    def label(self) -> str: ...


def build_context_label(
    *,
    class_level: str,
    subject: str,
    chapter: ChapterLike | None,
    topic: TopicLike | None,
    exercise: ExerciseLike | None,
    content_type: str,
    meta: Mapping[str, str],
) -> str:
    parts = [ClassLevel(class_level).label, subject]
    if chapter is not None:
        parts.append(chapter_label(chapter.number, chapter.title))
        if topic is not None:
            parts.append(f"{topic.number} {topic.title}" if topic.number else topic.title)
        if exercise is not None:
            parts.append(f"Exercise {exercise.label}".strip())
    if number := meta.get("question_number"):
        parts.append(f"Question {number}")
    if number := meta.get("example_number"):
        parts.append(f"Example {number}")
    if content_type == ContentType.SUMMARY:
        parts.append("Summary")
    return SEPARATOR.join(part for part in parts if part)[:MAX_LENGTH]
