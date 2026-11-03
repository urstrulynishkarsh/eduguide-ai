"""Children (for parents) and the learner's own profile (for students)."""

import uuid

from fastapi import APIRouter, Response, status

from app.api.deps import CurrentPrincipal, DbSession, ParentPrincipal
from app.auth import service as auth_service
from app.models import Student
from app.schemas.auth import ChildSessionResponse
from app.schemas.student import StudentCreate, StudentOut, StudentProfileIn, StudentUpdate
from app.services import student_service

router = APIRouter(prefix="/students", tags=["Students"])


@router.post("", response_model=StudentOut, status_code=status.HTTP_201_CREATED, summary="Add a child")
async def add_child(data: StudentCreate, principal: ParentPrincipal, db: DbSession) -> Student:
    """The "Add Child" form. Parents only. The class is validated first because
    the allowed stream and goals depend on it."""
    return await student_service.create_student(db, principal, data)


@router.get("", response_model=list[StudentOut], summary="List my children")
async def list_students(principal: CurrentPrincipal, db: DbSession) -> list[Student]:
    """A parent gets all their children. A student session gets only itself."""
    return await student_service.list_students(db, principal)


@router.get("/{student_id}", response_model=StudentOut, summary="Get one child")
async def get_student(student_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession) -> Student:
    return await student_service.get_student(db, principal, student_id)


@router.patch("/{student_id}", response_model=StudentOut, summary="Change name or age")
async def update_student(
    student_id: uuid.UUID, data: StudentUpdate, principal: CurrentPrincipal, db: DbSession
) -> Student:
    return await student_service.update_student(db, principal, student_id, data)


@router.put("/{student_id}/profile", response_model=StudentOut, summary="Set class, board, language and goal")
async def set_profile(
    student_id: uuid.UUID, data: StudentProfileIn, principal: CurrentPrincipal, db: DbSession
) -> Student:
    """Replaces the whole learning profile. Used by parents to edit a child and
    by a self-registered student to finish onboarding."""
    return await student_service.set_profile(db, principal, student_id, data)


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Remove a child")
async def delete_student(student_id: uuid.UUID, principal: ParentPrincipal, db: DbSession) -> Response:
    """Parents only. Permanently deletes the child and all of the child's learning data."""
    await student_service.delete_student(db, principal, student_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{student_id}/session",
    response_model=ChildSessionResponse,
    summary="Start child mode for one child",
)
async def start_child_session(
    student_id: uuid.UUID, principal: ParentPrincipal, db: DbSession
) -> ChildSessionResponse:
    """A parent hands the device to a child. The returned token can only act as
    this child: no siblings, no profile changes, no parent screens."""
    token, seconds_valid, student = await auth_service.start_child_session(db, principal, student_id)
    return ChildSessionResponse(
        access_token=token,
        expires_in=seconds_valid,
        student=StudentOut.model_validate(student),
    )
