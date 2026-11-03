"""Create demo accounts so the app has something to show.

    python -m scripts.seed

Creates (only if they do not exist yet):

    parent@example.com  / DemoParent123     Sunita Sharma, with two children:
                                            Aarav (Class 7, CBSE) and Anaya (UKG),
                                            a sample book for each in "My Books", and
                                            demo practice questions for both books
    student@example.com / DemoStudent123    Kabir Verma, Class 12 Science, preparing for JEE

The demo practice questions (scripts/demo_questions.py) let practice work without an AI key.
Each learner is given a question only once, so they last for a few sessions per child.

These passwords are public. The script refuses to run in production.
"""

import asyncio
import io
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import select

from app.auth import service as auth_service
from app.auth.principal import Principal
from app.core.config import get_settings
from app.core.database import SessionLocal, engine
from app.core.enums import Board, ClassLevel, Goal, MaterialType, Role, Stream
from app.core.tasks import get_task_queue
from app.models import Book, Chapter, DocumentChunk, Exercise, PracticeSession, Question, Student, User
from app.question_generation.schemas import GeneratedQuestion
from app.schemas.auth import RegisterRequest
from app.schemas.library import BookCreate
from app.schemas.student import StudentCreate, StudentProfileIn
from app.services import document_service, library_service, question_bank, student_service
from app.storage import get_file_storage
from scripts.demo_questions import CLASS_7_MATHS, UKG_PICTURES

PARENT_EMAIL = "parent@example.com"
PARENT_PASSWORD = "DemoParent123"
STUDENT_EMAIL = "student@example.com"
STUDENT_PASSWORD = "DemoStudent123"
SAMPLE_DATA = Path(__file__).parent / "sample_data"
# (child, title, subject, file, demo questions)
SAMPLE_BOOKS = [
    ("Aarav", "Sample: Class 7 Mathematics", "Mathematics", "class7-maths-sample.txt", CLASS_7_MATHS),
    ("Anaya", "Sample: UKG Picture Book", "Hindi", "ukg-picture-book-sample.txt", UKG_PICTURES),
]

CHILDREN = [
    StudentCreate(
        name="Aarav",
        age=12,
        profile=StudentProfileIn(
            class_level=ClassLevel.CLASS_7,
            board=Board.CBSE,
            medium="en",
            primary_language="hinglish",
            subjects=["Mathematics", "Science", "Social Science", "English", "Hindi"],
        ),
    ),
    StudentCreate(
        name="Anaya",
        age=5,
        profile=StudentProfileIn(
            class_level=ClassLevel.UKG,
            board=Board.CBSE,
            medium="en",
            primary_language="hi",
            subjects=["English", "Hindi", "Maths"],
        ),
    ),
]

SOLO_STUDENT_PROFILE = StudentProfileIn(
    class_level=ClassLevel.CLASS_12,
    board=Board.CBSE,
    medium="en",
    primary_language="en",
    stream=Stream.SCIENCE,
    goal=Goal.JEE,
    subjects=["Physics", "Chemistry", "Mathematics", "English"],
)


async def _seed_parent() -> None:
    async with SessionLocal() as db:
        if await db.scalar(select(User.id).where(User.email == PARENT_EMAIL)) is not None:
            print(f"= {PARENT_EMAIL} already exists")
            return
        user = await auth_service.register_user(
            db,
            RegisterRequest(
                role=Role.PARENT,
                full_name="Sunita Sharma",
                email=PARENT_EMAIL,
                password=PARENT_PASSWORD,
                preferred_language="hinglish",
            ),
        )
        principal = Principal(user=user, role=Role.PARENT)
        for child in CHILDREN:
            await student_service.create_student(db, principal, child)
        print(f"+ {PARENT_EMAIL} / {PARENT_PASSWORD}  (children: Aarav - Class 7, Anaya - UKG)")


async def _seed_solo_student() -> None:
    async with SessionLocal() as db:
        if await db.scalar(select(User.id).where(User.email == STUDENT_EMAIL)) is not None:
            print(f"= {STUDENT_EMAIL} already exists")
            return
        user = await auth_service.register_user(
            db,
            RegisterRequest(
                role=Role.STUDENT,
                full_name="Kabir Verma",
                email=STUDENT_EMAIL,
                password=STUDENT_PASSWORD,
            ),
        )
        student = await db.scalar(select(Student).where(Student.user_id == user.id))
        assert student is not None
        principal = Principal(user=user, role=Role.STUDENT, student=student)
        await student_service.set_profile(db, principal, student.id, SOLO_STUDENT_PROFILE)
        print(f"+ {STUDENT_EMAIL} / {STUDENT_PASSWORD}  (Kabir - Class 12 Science, JEE)")


async def _seed_sample_book(child_name: str, title: str, subject: str, file_name: str) -> Book | None:
    """A small sample chapter for one child, read now instead of in the background."""
    async with SessionLocal() as db:
        user = await db.scalar(select(User).where(User.email == PARENT_EMAIL))
        if user is None:
            return None
        existing = await db.scalar(select(Book).where(Book.owner_user_id == user.id, Book.title == title))
        if existing is not None:
            print(f"= {title} already exists")
            return existing
        principal = Principal(user=user, role=Role.PARENT)
        child = next(s for s in await student_service.list_students(db, principal) if s.name == child_name)
        book = await library_service.create_book(
            db,
            principal,
            BookCreate(
                title=title, subject=subject, material_type=MaterialType.TEXTBOOK, student_id=child.id
            ),
        )
        file = SAMPLE_DATA / file_name
        upload = UploadFile(io.BytesIO(file.read_bytes()), filename=file.name)
        queue = get_task_queue()
        document = await document_service.upload_document(
            db, principal, book.id, upload, storage=get_file_storage(), queue=queue
        )
        await queue.wait_idle()
        await db.refresh(document)
        found = document.stats
        print(
            f"+ {title} for {child_name} ({document.status}: {found.get('chapters', 0)} chapter, "
            f"{found.get('exercises', 0)} exercises, {found.get('questions', 0)} questions)"
        )
        return book


async def _seed_demo_questions(book: Book, questions: list[tuple[str | None, GeneratedQuestion]]) -> None:
    """Puts the hand-written questions in the family's question bank, as if the AI had written them.
    Run again, it adds only those not there yet (new demo questions reach an existing database)."""
    async with SessionLocal() as db:
        there = set(
            (await db.scalars(select(Question.body["text"].astext).where(Question.book_id == book.id))).all()
        )
        questions = [(label, question) for label, question in questions if question.text not in there]
        if not questions:
            print(f"= practice questions for {book.title} already exist")
            return
        child = await db.get(Student, book.student_id)
        chapter = await db.scalar(
            select(Chapter).where(Chapter.book_id == book.id).order_by(Chapter.position)
        )
        if child is None or child.profile is None or chapter is None:
            print(f"! {book.title} has no chapter; no practice questions added")
            return
        exercises = {
            exercise.label: exercise
            for exercise in await db.scalars(select(Exercise).where(Exercise.chapter_id == chapter.id))
        }
        for exercise_label, generated in questions:
            exercise = exercises.get(exercise_label) if exercise_label else None
            place = (
                DocumentChunk.exercise_id == exercise.id
                if exercise
                else DocumentChunk.chapter_id == chapter.id
            )
            chunk = await db.scalar(
                select(DocumentChunk)
                .where(DocumentChunk.book_id == book.id, place)
                .order_by(DocumentChunk.position)
            )
            assert chunk is not None
            # A stand-in session: only the place and the language are read from it.
            session = PracticeSession(
                exercise_id=exercise.id if exercise else None, language=child.profile.primary_language
            )
            question = question_bank.to_question(generated, book.owner_user_id, session, child, {"S1": chunk})
            question.validation = {"checked_by": "written by hand (demo data)"}
            db.add(question)
        await db.commit()
        print(f"+ {len(questions)} demo practice questions for {book.title}")


async def main() -> None:
    if get_settings().is_production:
        raise SystemExit("Refusing to create demo accounts with public passwords in production.")
    try:
        await _seed_parent()
        await _seed_solo_student()
        for child_name, title, subject, file_name, questions in SAMPLE_BOOKS:
            book = await _seed_sample_book(child_name, title, subject, file_name)
            if book is not None:
                await _seed_demo_questions(book, questions)
    finally:
        await engine.dispose()
    print("Done. Sign in at http://localhost:3000 (or the API at http://localhost:8000/docs)")


if __name__ == "__main__":
    asyncio.run(main())
