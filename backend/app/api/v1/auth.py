"""Sign-up, sign-in and "who am I"."""

from fastapi import APIRouter, Request, Response, status

from app.api.deps import CurrentPrincipal, DbSession, RateCounter, client_address, limit_address
from app.auth import service as auth_service
from app.core import rate_limits
from app.schemas.auth import (
    AccountUpdate,
    AuthResponse,
    LoginRequest,
    LogoutRequest,
    MeResponse,
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
    """Ends the session of the token sent (the refresh token, or in child mode the access token):
    none of its tokens work any more. Always `204`, also for a session that has ended already."""
    await auth_service.sign_out(db, data.token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
        active_role=principal.role,
        active_student=StudentOut.model_validate(principal.student) if principal.student else None,
        onboarding_complete=onboarding_complete,
    )
