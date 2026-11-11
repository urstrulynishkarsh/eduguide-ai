"""Sign-up, sign-in and token schemas."""

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field, StringConstraints

from app.core.enums import Role
from app.core.languages import DEFAULT_LANGUAGE, is_content_language
from app.schemas.student import StudentOut

Password = Annotated[str, Field(min_length=8, max_length=128)]
PersonName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


def _supported(language: str) -> str:
    if not is_content_language(language):
        raise ValueError("This language is not available yet.")
    return language


# The language of the screens (and of the AI for a parent): one the platform can use today.
ScreenLanguage = Annotated[str, AfterValidator(_supported)]

PIN_LENGTH = 4


def _pin(pin: str) -> str:
    if len(pin) != PIN_LENGTH or not (pin.isascii() and pin.isdigit()):
        raise ValueError(f"The PIN is {PIN_LENGTH} digits.")
    return pin


# The parent PIN, which leaves child mode: typed on an on-screen number pad.
Pin = Annotated[str, AfterValidator(_pin)]


class RegisterRequest(BaseModel):
    role: Role
    full_name: PersonName
    email: EmailStr
    password: Password
    preferred_language: ScreenLanguage = DEFAULT_LANGUAGE


class AccountUpdate(BaseModel):
    preferred_language: ScreenLanguage


CurrentPassword = Annotated[str, Field(min_length=1, max_length=128)]


class LoginRequest(BaseModel):
    email: EmailStr
    password: CurrentPassword


class PinUpdate(BaseModel):
    password: CurrentPassword = Field(description="The account's password: only the parent sets the PIN.")
    pin: Pin


class LeaveChildModeRequest(BaseModel):
    pin: Pin


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    # Any token of the session: its access or its refresh token.
    token: str = Field(min_length=1, max_length=4096)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    role: Role
    preferred_language: str
    created_at: datetime


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Seconds until the access token expires.")


class AuthResponse(BaseModel):
    user: UserOut
    tokens: TokenPair


class ChildSessionResponse(TokenPair):
    """Tokens that can only act as one child, also when they are renewed. Child mode ends with the
    parent PIN (`POST /auth/child-mode/leave`)."""

    student: StudentOut


class MeResponse(BaseModel):
    user: UserOut
    pin_set: bool = Field(description="The parent PIN is set (child mode needs one). False for a student.")
    active_role: Role = Field(description='"student" while a parent has the app in child mode.')
    active_student: StudentOut | None = Field(description="The learner this session is limited to, if any.")
    onboarding_complete: bool = Field(
        description="False until a parent has added a child, or a student has filled in their class details."
    )
