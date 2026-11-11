"""Sign-up, sign-in, tokens, child mode and the parent PIN."""

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
_WRONG_PIN = "The PIN is not correct."


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
    if principal.is_child_mode:
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


async def _new_session(db: AsyncSession, user: User, student_id: uuid.UUID | None = None) -> AuthSession:
    """A sign-in, or child mode for one child (`student_id`)."""
    now = utcnow()
    # The account's sessions that ran out or were signed out are of no more use.
    await db.execute(
        delete(AuthSession).where(
            AuthSession.user_id == user.id,
            or_(AuthSession.expires_at < now, AuthSession.revoked_at.is_not(None)),
        )
    )
    session = AuthSession(
        user_id=user.id,
        student_id=student_id,
        created_at=now,
        expires_at=now + timedelta(days=get_settings().refresh_token_expire_days),
    )
    db.add(session)
    await db.flush()
    return session


async def _tokens(db: AsyncSession, user: User, session: AuthSession) -> TokenPair:
    """New tokens for a session: a parent's, a student's own, or child mode (the session's child)."""
    settings = get_settings()
    role = Role(user.role)
    student_id = session.student_id
    if student_id is not None:
        role = Role.STUDENT
    elif role is Role.STUDENT:
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
    return await _tokens(db, user, await _new_session(db, user))


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
    ignored (the session has ended already, or the token is not one of ours). Child mode is refused:
    only the parent PIN ends it (`leave_child_mode`)."""
    for token_type in TokenType:
        try:
            payload = decode_token(token, expected_type=token_type)
            break
        except TokenError:
            continue
    else:
        return
    session = await db.get(AuthSession, payload.session_id)
    if session is None or session.user_id != payload.user_id or session.revoked_at is not None:
        return
    if session.student_id is not None:
        raise PermissionDeniedError("Child mode is left with the parent PIN.", code="pin_required")
    session.revoked_at = utcnow()
    await db.commit()


async def has_pin(db: AsyncSession, user: User) -> bool:
    """The parent PIN is set. Never for a student's own account (it has no parent record)."""
    return bool(await db.scalar(select(Parent.pin_hash.is_not(None)).where(Parent.user_id == user.id)))


async def set_pin(db: AsyncSession, principal: Principal, password: str, pin: str) -> None:
    """Sets or changes the parent PIN. Only in a parent's own session (not child mode), and only with
    the account's password, so whoever holds a parent's open screen can't change it either."""
    user = principal.user
    if not await run_in_threadpool(verify_password, password, user.password_hash):
        raise AuthenticationError("The password is not correct.", code="wrong_password")
    parent = await db.scalar(select(Parent).where(Parent.user_id == user.id))
    parent.pin_hash = await run_in_threadpool(hash_password, pin)  # slow on purpose
    await db.commit()


async def leave_child_mode(db: AsyncSession, principal: Principal, pin: str) -> TokenPair:
    """Child mode ends with the parent PIN: its session is signed out and the parent signs in anew,
    with a session of their own (tokens as at sign-in)."""
    if not principal.is_child_mode:
        raise PermissionDeniedError("This device is not in child mode.", code="not_child_mode")
    user = principal.user
    pin_hash = await db.scalar(select(Parent.pin_hash).where(Parent.user_id == user.id))
    if pin_hash is None or not await run_in_threadpool(verify_password, pin, pin_hash):
        raise AuthenticationError(_WRONG_PIN, code="wrong_pin")
    child_session = await db.get(AuthSession, principal.session_id)
    child_session.revoked_at = utcnow()
    return await issue_tokens(db, user)


async def start_child_session(
    db: AsyncSession, principal: Principal, student_id: uuid.UUID
) -> tuple[TokenPair, Student]:
    """A parent hands the device to a child: a child-mode session, which needs the parent PIN set.

    Its tokens still belong to the parent's account but can only act as this one child: no
    siblings, no profile changes, no parent screen. They are renewed like a sign-in's, as this
    child only, until the parent PIN ends child mode.
    """
    student = await student_service.get_student(db, principal, student_id)  # 404 unless it is their child
    if not await has_pin(db, principal.user):
        raise ConflictError("Set a parent PIN before handing the device to a child.", code="pin_not_set")
    session = await _new_session(db, principal.user, student.id)
    return await _tokens(db, principal.user, session), student
