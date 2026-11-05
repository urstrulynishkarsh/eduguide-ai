"""Password hashing and tokens. No database needed."""

import uuid
from datetime import timedelta

import jwt
import pytest

from app.core.config import get_settings
from app.core.enums import Role
from app.core.security import (
    TokenError,
    TokenType,
    create_token,
    decode_token,
    hash_password,
    verify_password,
)


def _access_token(**overrides):
    values = {
        "user_id": uuid.uuid4(),
        "role": Role.PARENT,
        "token_type": TokenType.ACCESS,
        "expires_in": timedelta(minutes=5),
        "session_id": uuid.uuid4(),
        **overrides,
    }
    return create_token(**values)


def test_password_is_hashed_and_can_be_verified():
    hashed = hash_password("correct horse battery staple")
    assert hashed != "correct horse battery staple"
    assert hashed.startswith("$argon2id$")
    assert verify_password("correct horse battery staple", hashed)
    assert not verify_password("wrong password", hashed)


def test_the_same_password_never_hashes_to_the_same_value():
    assert hash_password("same-password") != hash_password("same-password")


def test_verify_password_survives_a_broken_hash():
    assert not verify_password("anything", "this-is-not-a-hash")


def test_token_round_trip_keeps_user_role_session_and_student():
    user_id, session_id, student_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    token = _access_token(user_id=user_id, role=Role.STUDENT, session_id=session_id, student_id=student_id)
    payload = decode_token(token, expected_type=TokenType.ACCESS)
    assert payload.user_id == user_id
    assert payload.role is Role.STUDENT
    assert payload.session_id == session_id
    assert payload.student_id == student_id


def test_token_without_a_session_is_rejected():
    """Tokens made before sessions existed (Step 12) stop working: everyone signs in once more."""
    settings = get_settings()
    token = jwt.encode(
        {"sub": str(uuid.uuid4()), "role": "parent", "type": "access", "exp": 9999999999},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(TokenError):
        decode_token(token, expected_type=TokenType.ACCESS)


def test_parent_token_has_no_student():
    payload = decode_token(_access_token(), expected_type=TokenType.ACCESS)
    assert payload.role is Role.PARENT
    assert payload.student_id is None


def test_expired_token_is_rejected():
    with pytest.raises(TokenError):
        decode_token(_access_token(expires_in=timedelta(seconds=-1)), expected_type=TokenType.ACCESS)


def test_refresh_token_cannot_be_used_as_access_token_and_vice_versa():
    refresh = _access_token(token_type=TokenType.REFRESH)
    with pytest.raises(TokenError):
        decode_token(refresh, expected_type=TokenType.ACCESS)
    with pytest.raises(TokenError):
        decode_token(_access_token(), expected_type=TokenType.REFRESH)


def test_tampered_token_is_rejected():
    token = _access_token()
    header, body, signature = token.split(".")
    flipped = ("A" if signature[0] != "A" else "B") + signature[1:]
    with pytest.raises(TokenError):
        decode_token(f"{header}.{body}.{flipped}", expected_type=TokenType.ACCESS)


def test_token_signed_with_another_secret_is_rejected():
    forged = jwt.encode(
        {"sub": str(uuid.uuid4()), "role": "parent", "type": "access", "exp": 9999999999},
        "some-other-secret-that-is-long-enough-000000",
        algorithm="HS256",
    )
    with pytest.raises(TokenError):
        decode_token(forged, expected_type=TokenType.ACCESS)


def test_unsigned_token_is_rejected():
    unsigned = jwt.encode(
        {"sub": str(uuid.uuid4()), "role": "parent", "type": "access", "exp": 9999999999},
        key="",
        algorithm="none",
    )
    with pytest.raises(TokenError):
        decode_token(unsigned, expected_type=TokenType.ACCESS)


@pytest.mark.parametrize("garbage", ["", "not-a-token", "a.b.c"])
def test_garbage_is_rejected(garbage):
    with pytest.raises(TokenError):
        decode_token(garbage, expected_type=TokenType.ACCESS)


def test_token_with_an_unknown_role_is_rejected():
    settings = get_settings()
    token = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "role": "admin",
            "type": "access",
            "ses": str(uuid.uuid4()),
            "exp": 9999999999,
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(TokenError):
        decode_token(token, expected_type=TokenType.ACCESS)
