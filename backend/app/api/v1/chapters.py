"""Chapters and exercises found in a book."""

import uuid

from fastapi import APIRouter

from app.api.deps import CurrentPrincipal, DbSession
from app.api.v1.library_views import chapter_detail, exercise_detail
from app.models import Chapter
from app.schemas.library import ChapterDetail, ChapterUpdate, ExerciseDetail
from app.services import library_service

router = APIRouter(tags=["My Books"])


async def _chapter_response(db: DbSession, chapter: Chapter) -> ChapterDetail:
    counts = await library_service.chapter_details(db, [chapter.id])
    topics, exercises = await library_service.chapter_contents(db, chapter)
    return chapter_detail(chapter, counts[chapter.id], topics, exercises)


@router.get("/chapters/{chapter_id}", response_model=ChapterDetail, summary="A chapter: topics and exercises")
async def get_chapter(chapter_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession) -> ChapterDetail:
    return await _chapter_response(db, await library_service.get_chapter(db, principal, chapter_id))


@router.patch(
    "/chapters/{chapter_id}", response_model=ChapterDetail, summary="Rename a chapter or fix its number"
)
async def update_chapter(
    chapter_id: uuid.UUID, data: ChapterUpdate, principal: CurrentPrincipal, db: DbSession
) -> ChapterDetail:
    return await _chapter_response(db, await library_service.update_chapter(db, principal, chapter_id, data))


@router.get("/exercises/{exercise_id}", response_model=ExerciseDetail, summary="The questions of an exercise")
async def get_exercise(exercise_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession) -> ExerciseDetail:
    """Questions exactly as printed in the book (`origin: "textbook"`), each with its source."""
    exercise, chapter, book = await library_service.get_exercise(db, principal, exercise_id)
    questions = await library_service.exercise_questions(db, exercise)
    return exercise_detail(exercise, chapter, book, questions)
