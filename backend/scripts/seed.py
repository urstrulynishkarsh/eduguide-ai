"""Create demo accounts so the app has something to show.

    python -m scripts.seed

Creates (only if they do not exist yet):

    parent@example.com  / DemoParent123     Sunita Sharma, with two children:
                                            Aarav (Class 7, CBSE) and Anaya (UKG)
    student@example.com / DemoStudent123    Kabir Verma, Class 12 Science, preparing for JEE

These passwords are public. The script refuses to run in production.
"""

import asyncio

from sqlalchemy import select

from app.auth import service as auth_service
from app.auth.principal import Principal
from app.core.config import get_settings
from app.core.database import SessionLocal, engine
from app.core.enums import Board, ClassLevel, Goal, Role, Stream
from app.models import Student, User
from app.schemas.auth import RegisterRequest
from app.schemas.student import StudentCreate, StudentProfileIn
from app.services import student_service

PARENT_EMAIL = "parent@example.com"
PARENT_PASSWORD = "DemoParent123"
STUDENT_EMAIL = "student@example.com"
STUDENT_PASSWORD = "DemoStudent123"

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


async def main() -> None:
    if get_settings().is_production:
        raise SystemExit("Refusing to create demo accounts with public passwords in production.")
    try:
        await _seed_parent()
        await _seed_solo_student()
    finally:
        await engine.dispose()
    print("Done. Sign in at http://localhost:8000/docs -> POST /api/v1/auth/login")


if __name__ == "__main__":
    asyncio.run(main())
