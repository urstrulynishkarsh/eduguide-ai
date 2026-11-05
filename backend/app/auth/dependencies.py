"""FastAPI dependencies that answer "who is calling, and may they do this?"."""

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.principal import Principal
from app.core.database import get_db
from app.core.enums import Role
from app.core.errors import AuthenticationError, PermissionDeniedError
from app.core.security import TokenError, TokenType, decode_token
from app.models import AuthSession, Student, User
from app.services.student_service import owned_by

_bearer = HTTPBearer(auto_error=False, description="Paste the `access_token` you got from /auth/login.")

_BAD_SESSION = "Your session has expired. Please sign in again."


async def get_current_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Principal:
    if credentials is None:
        raise AuthenticationError()

    try:
        payload = decode_token(credentials.credentials, expected_type=TokenType.ACCESS)
    except TokenError:
        raise AuthenticationError(_BAD_SESSION, code="invalid_token") from None

    # The account, if the token's session has not been signed out.
    user = await db.scalar(
        select(User)
        .join(AuthSession, AuthSession.user_id == User.id)
        .where(
            User.id == payload.user_id, AuthSession.id == payload.session_id, AuthSession.revoked_at.is_(None)
        )
    )
    if user is None or not user.is_active:
        raise AuthenticationError(_BAD_SESSION, code="invalid_token")

    if payload.role is Role.PARENT:
        if user.role != Role.PARENT:
            raise AuthenticationError(_BAD_SESSION, code="invalid_token")
        return Principal(user=user, role=Role.PARENT)

    # A student session: either a student's own login or a parent in child mode.
    # Checked on every request, so the token stops working if the child is removed.
    student = None
    if payload.student_id is not None:
        student = await db.scalar(select(Student).where(Student.id == payload.student_id, owned_by(user.id)))
    if student is None:
        raise AuthenticationError(_BAD_SESSION, code="invalid_token")
    return Principal(user=user, role=Role.STUDENT, student=student)


CurrentPrincipal = Annotated[Principal, Depends(get_current_principal)]


async def require_parent(principal: CurrentPrincipal) -> Principal:
    if not principal.is_parent:
        raise PermissionDeniedError("This is only available to parents.", code="parent_required")
    return principal


ParentPrincipal = Annotated[Principal, Depends(require_parent)]
