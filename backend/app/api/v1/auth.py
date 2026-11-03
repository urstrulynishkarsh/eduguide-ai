"""Sign-up, sign-in and "who am I"."""

from fastapi import APIRouter, status

from app.api.deps import CurrentPrincipal, DbSession
from app.auth import service as auth_service
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
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
async def login(data: LoginRequest, db: DbSession) -> AuthResponse:
    user = await auth_service.authenticate(db, data.email, data.password)
    tokens = await auth_service.issue_tokens(db, user)
    return AuthResponse(user=UserOut.model_validate(user), tokens=tokens)


@router.post("/refresh", response_model=TokenPair, summary="Swap a refresh token for new tokens")
async def refresh(data: RefreshRequest, db: DbSession) -> TokenPair:
    return await auth_service.refresh_tokens(db, data.refresh_token)


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
