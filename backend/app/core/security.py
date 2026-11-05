"""Password hashing and signed tokens.

Passwords are hashed with Argon2id. Tokens are JWTs with these claims:

    sub   the account (users.id) that signed in
    role  what this token may act as: "parent" or "student"
    sid   the learner (students.id) this token is limited to - student tokens only
    ses   the session (auth_sessions.id) it belongs to; signing out revokes the session
    type  "access" (sent with every request) or "refresh" (only used to get new tokens)

A parent who hands the device to a child gets a token with their own `sub`,
role "student" and the child's `sid`. See docs/01-architecture.md, "Identity".
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import get_settings
from app.core.enums import Role

_password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


class TokenError(Exception):
    """The token is missing something, expired, tampered with, or of the wrong type."""


@dataclass(frozen=True, slots=True)
class TokenPayload:
    user_id: uuid.UUID
    role: Role
    token_type: TokenType
    session_id: uuid.UUID
    student_id: uuid.UUID | None = None


def create_token(
    *,
    user_id: uuid.UUID,
    role: Role,
    token_type: TokenType,
    expires_in: timedelta,
    session_id: uuid.UUID,
    student_id: uuid.UUID | None = None,
) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    claims: dict[str, object] = {
        "sub": str(user_id),
        "role": role.value,
        "type": token_type.value,
        "ses": str(session_id),
        "iat": now,
        "exp": now + expires_in,
        "jti": uuid.uuid4().hex,
    }
    if student_id is not None:
        claims["sid"] = str(student_id)
    return jwt.encode(claims, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str, *, expected_type: TokenType) -> TokenPayload:
    settings = get_settings()
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "role", "type", "ses", "exp"]},
        )
        payload = TokenPayload(
            user_id=uuid.UUID(claims["sub"]),
            role=Role(claims["role"]),
            token_type=TokenType(claims["type"]),
            session_id=uuid.UUID(claims["ses"]),
            student_id=uuid.UUID(claims["sid"]) if claims.get("sid") else None,
        )
    except (jwt.PyJWTError, ValueError, KeyError, TypeError) as exc:
        raise TokenError("The token is not valid.") from exc

    if payload.token_type is not expected_type:
        raise TokenError(f"Expected {expected_type.value} token, got {payload.token_type.value}.")
    return payload
