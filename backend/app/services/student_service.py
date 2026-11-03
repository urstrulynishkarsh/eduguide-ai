"""Children / learners.

Every query in this file is limited to the learners the caller owns. This is
where "a parent can never see another parent's child" is enforced, so always
come through these functions instead of querying `Student` directly.
"""

import uuid

from sqlalchemy import ColumnElement, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.principal import Principal
from app.class_profiles import ClassProfile, check_learning_choices, get_class_profile, resolve_goal
from app.core.config import get_settings
from app.core.enums import Board, ClassLevel, Role
from app.core.errors import ConflictError, InvalidInputError, NotFoundError, PermissionDeniedError
from app.models import Parent, Student, StudentProfile
from app.schemas.student import StudentCreate, StudentProfileIn, StudentUpdate


def owned_by(user_id: uuid.UUID) -> ColumnElement[bool]:
    """SQL condition: the learner belongs to this account (as its child, or as the student itself)."""
    return or_(
        Student.user_id == user_id,
        Student.parent.has(Parent.user_id == user_id),
    )


def visible_to(principal: Principal) -> ColumnElement[bool]:
    """A parent sees all their children. A student session sees only its own learner."""
    condition = owned_by(principal.user.id)
    if principal.role is Role.STUDENT:
        condition = and_(condition, Student.id == principal.student_id)
    return condition


def _ensure_can_manage(principal: Principal, student: Student) -> None:
    """Parents manage their children. A student who signed up alone manages themself.

    A child using the app in child mode cannot change their own class or name.
    """
    if principal.is_parent or student.user_id == principal.user.id:
        return
    raise PermissionDeniedError("Only a parent can change this.", code="parent_required")


def _profile_values(data: StudentProfileIn) -> dict[str, object]:
    """Check the class / stream / goal combination and return the columns to store."""
    goal = resolve_goal(data.class_level, data.goal)
    problems = check_learning_choices(data.class_level, data.stream, goal)
    if problems:
        raise InvalidInputError(
            problems[0].message,
            code="invalid_learning_profile",
            details=[{"field": problem.field, "message": problem.message} for problem in problems],
        )
    needs_board_name = data.board in (Board.STATE, Board.OTHER)
    return {
        "class_level": data.class_level.value,
        "board": data.board.value,
        "board_name": (data.board_name or None) if needs_board_name else None,
        "medium": data.medium,
        "primary_language": data.primary_language,
        "stream": data.stream.value if data.stream else None,
        "goal": goal.value,
        "subjects": list(data.subjects),
    }


async def list_students(db: AsyncSession, principal: Principal) -> list[Student]:
    result = await db.execute(
        select(Student).where(visible_to(principal)).order_by(Student.created_at, Student.id)
    )
    return list(result.scalars().all())


async def count_students(db: AsyncSession, principal: Principal) -> int:
    count = await db.scalar(select(func.count()).select_from(Student).where(visible_to(principal)))
    return count or 0


async def get_student(db: AsyncSession, principal: Principal, student_id: uuid.UUID) -> Student:
    """Load one learner, or raise 404 - also when it exists but belongs to someone else."""
    result = await db.execute(
        select(Student)
        .where(Student.id == student_id, visible_to(principal))
        .execution_options(populate_existing=True)
    )
    student = result.scalar_one_or_none()
    if student is None:
        raise NotFoundError("We couldn't find this student.", code="student_not_found")
    return student


async def learner_for(db: AsyncSession, principal: Principal, student_id: uuid.UUID | None) -> Student:
    """The learner a request is about: a student session is always itself; a parent names a child.
    The learner must have class details, because everything the AI does depends on them."""
    if principal.student is not None:
        student = principal.student
    elif student_id is None:
        raise InvalidInputError(
            "Please choose which child this is for.",
            details=[{"field": "student_id", "message": "Choose a child."}],
        )
    else:
        student = await get_student(db, principal, student_id)
    return require_profile(student)


def require_profile(student: Student) -> Student:
    if student.profile is None:
        raise InvalidInputError("Please fill in the class details first.", code="profile_required")
    return student


def class_profile(student: Student) -> ClassProfile:
    """The rules of the learner's class (the learner must have class details)."""
    assert student.profile is not None
    return get_class_profile(ClassLevel(student.profile.class_level))


async def account_of(db: AsyncSession, student: Student) -> uuid.UUID:
    """The account that owns this learner's data (the parent, or the student's own login)."""
    if student.user_id is not None:
        return student.user_id
    user_id = await db.scalar(select(Parent.user_id).where(Parent.id == student.parent_id))
    assert user_id is not None
    return user_id


async def create_student(db: AsyncSession, principal: Principal, data: StudentCreate) -> Student:
    """A parent adds a child."""
    parent_id = await db.scalar(select(Parent.id).where(Parent.user_id == principal.user.id))
    if not principal.is_parent or parent_id is None:
        raise PermissionDeniedError("Only a parent can add a child.", code="parent_required")

    limit = get_settings().max_students_per_parent
    if await count_students(db, principal) >= limit:
        raise ConflictError(f"You can add up to {limit} children.", code="student_limit_reached")

    student = Student(parent_id=parent_id, name=data.name, age=data.age)
    student.profile = StudentProfile(**_profile_values(data.profile))
    db.add(student)
    await db.commit()
    return await get_student(db, principal, student.id)


async def update_student(
    db: AsyncSession, principal: Principal, student_id: uuid.UUID, data: StudentUpdate
) -> Student:
    student = await get_student(db, principal, student_id)
    _ensure_can_manage(principal, student)

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(student, field, value)
    await db.commit()
    return await get_student(db, principal, student_id)


async def set_profile(
    db: AsyncSession, principal: Principal, student_id: uuid.UUID, data: StudentProfileIn
) -> Student:
    """Create or replace the learning profile (class, board, language, goal...)."""
    student = await get_student(db, principal, student_id)
    _ensure_can_manage(principal, student)

    values = _profile_values(data)
    if student.profile is None:
        student.profile = StudentProfile(**values)
    else:
        for field, value in values.items():
            setattr(student.profile, field, value)
    await db.commit()
    return await get_student(db, principal, student_id)


async def delete_student(db: AsyncSession, principal: Principal, student_id: uuid.UUID) -> None:
    """A parent removes a child and, with the child, all of that child's learning data."""
    student = await get_student(db, principal, student_id)
    if not principal.is_parent:
        raise PermissionDeniedError("Only a parent can remove a child.", code="parent_required")
    await db.delete(student)
    await db.commit()
