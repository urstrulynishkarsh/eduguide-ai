"""Who is making the current request."""

import uuid
from dataclasses import dataclass

from app.core.enums import Role
from app.models import Student, User


@dataclass(frozen=True, slots=True)
class Principal:
    """The signed-in account plus what this session is allowed to act as.

    `user`    - the account that signed in (it owns the data).
    `role`    - what this session may do. A parent in child mode has role "student".
    `student` - the single learner a student session is limited to; None for parents.
    `session_id` - the session of the request's token (auth_sessions.id).
    """

    user: User
    role: Role
    student: Student | None = None
    session_id: uuid.UUID | None = None

    @property
    def student_id(self) -> uuid.UUID | None:
        return self.student.id if self.student is not None else None

    @property
    def is_parent(self) -> bool:
        return self.role is Role.PARENT

    @property
    def is_child_mode(self) -> bool:
        """A parent's account acting as one of its children."""
        return self.role is Role.STUDENT and self.user.role == Role.PARENT
