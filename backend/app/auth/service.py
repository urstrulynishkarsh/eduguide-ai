"""Sign-up, sign-in, tokens and child mode."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.auth.principal import Principal
from app.core.config import get_settings
from app.core.enums import Role
from app.core.errors import AuthenticationError, ConflictError, PermissionDeniedError
from app.core.security import (
    TokenError,
    TokenType,
    create_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models import AuthSession, Parent, Student, User
from app.models.base import utcnow
from app.schemas.auth import AccountUpdate, RegisterRequest, TokenPair
from app.services import student_service

# Checked when the email is unknown, so "no such account" and "wrong password"
# take the same time and cannot be told apart from outside.
_DUMMY_PASSWORD_HASH = hash_password("not-a-real-password")

_EMAIL_TAKEN = "An account with this email already exists. Try signing in instead."
_BAD_LOGIN = "The email or password is not correct."
_BAD_SESSION = "Your session has expired. Please sign in again."


def normalize_email(email: str) -> str:
    return email.strip().lower()


async def register_user(db: AsyncSession, data: RegisterRequest) -> User:
    """Create an account. A parent gets a parent record; a student gets a learner record."""
    email = normalize_email(data.email)
    if await db.scalar(select(User.id).where(User.email == email)) is not None:
        raise ConflictError(_EMAIL_TAKEN, code="email_already_registered")

    user = User(
        email=email,
        password_hash=await run_in_threadpool(hash_password, data.password),  # slow on purpose
        full_name=data.full_name,
        role=data.role.value,
        preferred_language=data.preferred_language,
    )
    db.add(user)
    try:
        await db.flush()
        if data.role is Role.PARENT:
            db.add(Parent(user_id=user.id))
        else:
            # Class details are filled in on the next onboarding screen.
            db.add(Student(user_id=user.id, name=data.full_name))
        await db.commit()
    except IntegrityError:
        # Two sign-ups with the same email at the same moment.
        await db.rollback()
        raise ConflictError(_EMAIL_TAKEN, code="email_already_registered") from None
    return user


async def update_account(db: AsyncSession, principal: Principal, data: AccountUpdate) -> User:
    """The account's own settings. Not in child mode: the child must not change the parent's account."""
    if principal.role is Role.STUDENT and principal.user.role == Role.PARENT:
        raise PermissionDeniedError("Only the account holder can change this.", code="parent_required")
    principal.user.preferred_language = data.preferred_language
    await db.commit()
    return principal.user


async def authenticate(db: AsyncSession, email: str, password: str) -> User:
    user = await db.scalar(select(User).where(User.email == normalize_email(email)))
    password_ok = await run_in_threadpool(
        verify_password, password, user.password_hash if user else _DUMMY_PASSWORD_HASH
    )
    if user is None or not password_ok or not user.is_active:
        raise AuthenticationError(_BAD_LOGIN, code="invalid_credentials")

    user.last_login_at = datetime.now(UTC)
    await db.commit()
    return user


async def _new_session(db: AsyncSession, user: User, lasts: timedelta) -> AuthSession:
    now = utcnow()
    # The account's sessions that ran out or were signed out are of no more use.
    await db.execute(
        delete(AuthSession).where(
            AuthSession.user_id == user.id,
            or_(AuthSession.expires_at < now, AuthSession.revoked_at.is_not(None)),
        )
    )
    session = AuthSession(user_id=user.id, created_at=now, expires_at=now + lasts)
    db.add(session)
    await db.flush()
    return session


async def _tokens(db: AsyncSession, user: User, session: AuthSession) -> TokenPair:
    settings = get_settings()
    role = Role(user.role)
    student_id: uuid.UUID | None = None
    if role is Role.STUDENT:
        student_id = await db.scalar(select(Student.id).where(Student.user_id == user.id))

    refresh_lasts = timedelta(days=settings.refresh_token_expire_days)
    session.expires_at = utcnow() + refresh_lasts
    tokens = TokenPair(
        access_token=create_token(
            user_id=user.id,
            role=role,
            token_type=TokenType.ACCESS,
            expires_in=timedelta(minutes=settings.access_token_expire_minutes),
            session_id=session.id,
            student_id=student_id,
        ),
        refresh_token=create_token(
            user_id=user.id,
            role=role,
            token_type=TokenType.REFRESH,
            expires_in=refresh_lasts,
            session_id=session.id,
        ),
        expires_in=settings.access_token_expire_minutes * 60,
    )
    await db.commit()
    return tokens


async def issue_tokens(db: AsyncSession, user: User) -> TokenPair:
    """A new sign-in: a new session and its first tokens."""
    session = await _new_session(db, user, timedelta(days=get_settings().refresh_token_expire_days))
    return await _tokens(db, user, session)


async def refresh_tokens(db: AsyncSession, refresh_token: str) -> TokenPair:
    """New tokens for the same session, which lasts on from now. Refused once it was signed out."""
    try:
        payload = decode_token(refresh_token, expected_type=TokenType.REFRESH)
    except TokenError:
        raise AuthenticationError(_BAD_SESSION, code="invalid_token") from None

    user = await db.get(User, payload.user_id)
    session = await db.get(AuthSession, payload.session_id)
    if (
        user is None
        or not user.is_active
        or session is None
        or session.user_id != user.id
        or session.revoked_at is not None
    ):
        raise AuthenticationError(_BAD_SESSION, code="invalid_token")
    return await _tokens(db, user, session)


async def sign_out(db: AsyncSession, token: str) -> None:
    """Revokes the session of a token: an access or a refresh token, still valid. Anything else is
    ignored (the session has ended already, or the token is not one of ours)."""
    for token_type in TokenType:
        try:
            payload = decode_token(token, expected_type=token_type)
            break
        except TokenError:
            continue
    else:
        return
    session = await db.get(AuthSession, payload.session_id)
    if session is not None and session.user_id == payload.user_id and session.revoked_at is None:
        session.revoked_at = utcnow()
        await db.commit()


async def start_child_session(
    db: AsyncSession, principal: Principal, student_id: uuid.UUID
) -> tuple[str, int, Student]:
    """A parent hands the device to a child.

    Returns a token that still belongs to the parent's account but can only act
    as this one child: it cannot see siblings, change profiles or use any
    parent screen. Returns (token, seconds_valid, student).
    """
    student = await student_service.get_student(db, principal, student_id)  # 404 unless it is their child
    seconds_valid = get_settings().child_session_expire_minutes * 60
    session = await _new_session(db, principal.user, timedelta(seconds=seconds_valid))
    token = create_token(
        user_id=principal.user.id,
        role=Role.STUDENT,
        token_type=TokenType.ACCESS,
        expires_in=timedelta(seconds=seconds_valid),
        session_id=session.id,
        student_id=student.id,
    )
    await db.commit()
    return token, seconds_valid, student
