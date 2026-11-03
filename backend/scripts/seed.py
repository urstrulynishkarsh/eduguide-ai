"""Create demo accounts so the app has something to show.

    python -m scripts.seed

Creates (only if they do not exist yet):

    parent@example.com  / DemoParent123     Sunita Sharma, with two children:
                                            Aarav (Class 7, CBSE) and Anaya (UKG),
                                            and a sample book for Aarav in "My Books"
    student@example.com / DemoStudent123    Kabir Verma, Class 12 Science, preparing for JEE

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
from app.models import Book, Student, User
from app.schemas.auth import RegisterRequest
from app.schemas.library import BookCreate
from app.schemas.student import StudentCreate, StudentProfileIn
from app.services import document_service, library_service, student_service
from app.storage import get_file_storage

PARENT_EMAIL = "parent@example.com"
PARENT_PASSWORD = "DemoParent123"
STUDENT_EMAIL = "student@example.com"
STUDENT_PASSWORD = "DemoStudent123"
SAMPLE_BOOK_TITLE = "Sample: Class 7 Mathematics"
SAMPLE_BOOK_FILE = Path(__file__).parent / "sample_data" / "class7-maths-sample.txt"

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


async def _seed_sample_book() -> None:
    """A small sample chapter for Aarav, so "My Books" has something to show."""
    async with SessionLocal() as db:
        user = await db.scalar(select(User).where(User.email == PARENT_EMAIL))
        if user is None:
            return
        if await db.scalar(
            select(Book.id).where(Book.owner_user_id == user.id, Book.title == SAMPLE_BOOK_TITLE)
        ):
            print(f"= {SAMPLE_BOOK_TITLE} already exists")
            return
        principal = Principal(user=user, role=Role.PARENT)
        aarav = next(s for s in await student_service.list_students(db, principal) if s.name == "Aarav")
        book = await library_service.create_book(
            db,
            principal,
            BookCreate(
                title=SAMPLE_BOOK_TITLE,
                subject="Mathematics",
                material_type=MaterialType.TEXTBOOK,
                student_id=aarav.id,
            ),
        )
        upload = UploadFile(io.BytesIO(SAMPLE_BOOK_FILE.read_bytes()), filename=SAMPLE_BOOK_FILE.name)
        queue = get_task_queue()
        document = await document_service.upload_document(
            db, principal, book.id, upload, storage=get_file_storage(), queue=queue
        )
        await queue.wait_idle()  # read the book now instead of in the background
        await db.refresh(document)
        found = document.stats
        print(
            f"+ {SAMPLE_BOOK_TITLE} for Aarav ({document.status}: {found.get('chapters', 0)} chapter, "
            f"{found.get('exercises', 0)} exercises, {found.get('questions', 0)} questions)"
        )


async def main() -> None:
    if get_settings().is_production:
        raise SystemExit("Refusing to create demo accounts with public passwords in production.")
    try:
        await _seed_parent()
        await _seed_solo_student()
        await _seed_sample_book()
    finally:
        await engine.dispose()
    print("Done. Sign in at http://localhost:8000/docs -> POST /api/v1/auth/login")


if __name__ == "__main__":
    asyncio.run(main())
