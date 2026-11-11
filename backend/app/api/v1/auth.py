"""Sign-up, sign-in, "who am I", and the parent PIN that leaves child mode."""

from fastapi import APIRouter, Request, Response, status

from app.api.deps import (
    CurrentPrincipal,
    DbSession,
    ParentPrincipal,
    RateCounter,
    client_address,
    limit_address,
)
from app.auth import service as auth_service
from app.core import rate_limits
from app.schemas.auth import (
    AccountUpdate,
    AuthResponse,
    LeaveChildModeRequest,
    LoginRequest,
    LogoutRequest,
    MeResponse,
    PinUpdate,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
    UserOut,
)
from app.schemas.student import StudentOut
from app.services import student_service

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a parent or student account",
    dependencies=[limit_address(rate_limits.SIGN_UP_PER_ADDRESS)],
)
async def register(data: RegisterRequest, db: DbSession) -> AuthResponse:
    """The first onboarding screen: "Who are you? Parent / Student".

    The new account is signed in straight away (tokens are returned).
    Next step for a parent: `POST /students`. For a student: `PUT /students/{id}/profile`.
    """
    user = await auth_service.register_user(db, data)
    tokens = await auth_service.issue_tokens(db, user)
    return AuthResponse(user=UserOut.model_validate(user), tokens=tokens)


@router.post("/login", response_model=AuthResponse, summary="Sign in with email and password")
async def login(data: LoginRequest, request: Request, db: DbSession, counter: RateCounter) -> AuthResponse:
    """`429 too_many_requests` after 10 failed tries for one email in 15 minutes, or 60 from one
    address. Signing in that works is never counted."""
    email = auth_service.normalize_email(data.email)
    counted = (
        (rate_limits.SIGN_IN_PER_EMAIL, email),
        (rate_limits.SIGN_IN_PER_ADDRESS, client_address(request)),
    )
    async with rate_limits.failures(counter, *counted):
        user = await auth_service.authenticate(db, data.email, data.password)
    tokens = await auth_service.issue_tokens(db, user)
    return AuthResponse(user=UserOut.model_validate(user), tokens=tokens)


@router.post("/refresh", response_model=TokenPair, summary="Swap a refresh token for new tokens")
async def refresh(data: RefreshRequest, db: DbSession) -> TokenPair:
    return await auth_service.refresh_tokens(db, data.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Sign out")
async def logout(data: LogoutRequest, db: DbSession) -> Response:
    """Ends the session of the token sent (its access or refresh token): none of its tokens work any
    more. `204`, also for a session that has ended already. Child mode answers `403 pin_required`:
    only the parent PIN ends it (`POST /auth/child-mode/leave`)."""
    await auth_service.sign_out(db, data.token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/pin", status_code=status.HTTP_204_NO_CONTENT, summary="Set or change the parent PIN")
async def set_pin(
    data: PinUpdate, principal: ParentPrincipal, db: DbSession, counter: RateCounter
) -> Response:
    """The 4-digit PIN that leaves child mode; needed before the first hand-over. Needs the account's
    password (`401 wrong_password`), counted like a failed sign-in for the account's email."""
    async with rate_limits.failures(counter, (rate_limits.SIGN_IN_PER_EMAIL, principal.user.email)):
        await auth_service.set_pin(db, principal, data.password, data.pin)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/child-mode/leave", response_model=AuthResponse, summary="Leave child mode with the parent PIN")
async def leave_child_mode(
    data: LeaveChildModeRequest, principal: CurrentPrincipal, db: DbSession, counter: RateCounter
) -> AuthResponse:
    """Sent with the child-mode token. The right PIN ends child mode and signs the parent in (tokens
    as at sign-in); a wrong one is `401 wrong_pin`. 5 wrong PINs in 15 minutes, or 20 in a day, and
    the family waits (`429`). Anything but child mode is `403 not_child_mode`."""
    family = principal.user.id.hex
    counted = ((rate_limits.PIN_PER_ACCOUNT, family), (rate_limits.PIN_PER_DAY, family))
    async with rate_limits.failures(counter, *counted):
        tokens = await auth_service.leave_child_mode(db, principal, data.pin)
    return AuthResponse(user=UserOut.model_validate(principal.user), tokens=tokens)


@router.patch("/me", response_model=UserOut, summary="Change the account's screen language")
async def update_me(data: AccountUpdate, principal: CurrentPrincipal, db: DbSession) -> UserOut:
    """Settings: `preferred_language`, the language of the screens (en, hi, hinglish). Refused in
    child mode."""
    return UserOut.model_validate(await auth_service.update_account(db, principal, data))


@router.get("/me", response_model=MeResponse, summary="The signed-in account and its current mode")
async def me(principal: CurrentPrincipal, db: DbSession) -> MeResponse:
    if principal.student is not None:
        onboarding_complete = principal.student.profile is not None
    else:
        onboarding_complete = await student_service.count_students(db, principal) > 0
    return MeResponse(
        user=UserOut.model_validate(principal.user),
        pin_set=await auth_service.has_pin(db, principal.user),
        active_role=principal.role,
        active_student=StudentOut.model_validate(principal.student) if principal.student else None,
        onboarding_complete=onboarding_complete,
    )
