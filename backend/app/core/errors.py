"""Application errors and the single JSON shape every error is returned in.

    {"error": {"code": "student_not_found", "message": "...", "details": null}}

`code` is stable and meant for programs (the frontend maps it to a translated
message). `message` is plain English that is safe to show to a parent.
"""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base class for every error the application raises on purpose."""

    status_code: int = 400
    code: str = "bad_request"
    message: str = "The request could not be completed."

    def __init__(self, message: str | None = None, *, code: str | None = None, details: Any = None) -> None:
        self.message = message or self.message
        self.code = code or self.code
        self.details = details
        super().__init__(self.message)

    @property
    def headers(self) -> dict[str, str] | None:
        return None


class AuthenticationError(AppError):
    status_code = 401
    code = "not_authenticated"
    message = "Please sign in to continue."

    @property
    def headers(self) -> dict[str, str]:
        return {"WWW-Authenticate": "Bearer"}


class PermissionDeniedError(AppError):
    status_code = 403
    code = "permission_denied"
    message = "You are not allowed to do this."


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"
    message = "We couldn't find what you were looking for."


class ConflictError(AppError):
    status_code = 409
    code = "conflict"
    message = "This conflicts with something that already exists."


class TooManyRequestsError(AppError):
    """A rate limit (core/rate_limits.py). The `Retry-After` header says in how many seconds it may be
    tried again (`details` stays what it is everywhere: the fields at fault, here none)."""

    status_code = 429
    code = "too_many_requests"
    message = "Too many tries in a short time. Please wait a little and try again."

    def __init__(self, retry_after: int, *, daily: bool = False) -> None:
        super().__init__(
            "Today's allowance for this has been used. It starts again at midnight." if daily else None,
            code="daily_limit_reached" if daily else None,
        )
        self.retry_after = retry_after

    @property
    def headers(self) -> dict[str, str]:
        return {"Retry-After": str(self.retry_after)}


class InvalidInputError(AppError):
    status_code = 422
    code = "validation_error"
    message = "Some of the information is not valid."


def error_body(code: str, message: str, details: Any = None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details}}


_HTTP_STATUS_CODES = {
    400: "bad_request",
    401: "not_authenticated",
    403: "permission_denied",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    413: "payload_too_large",
    415: "unsupported_media_type",
    429: "too_many_requests",
}


def _field_path(location: tuple[Any, ...]) -> str:
    """("body", "profile", "class_level") -> "profile.class_level"."""
    parts = [str(part) for part in location]
    if parts and parts[0] in {"body", "query", "path", "header", "cookie"}:
        parts = parts[1:] or parts
    return ".".join(parts)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(exc.code, exc.message, exc.details),
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Only the field name and a readable message are returned. The submitted
        # values are deliberately left out (they can contain passwords).
        details = [
            {
                "field": _field_path(tuple(error.get("loc", ()))),
                "message": str(error.get("msg", "Invalid value")).removeprefix("Value error, "),
            }
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content=error_body("validation_error", InvalidInputError.message, details),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _HTTP_STATUS_CODES.get(exc.status_code, "error")
        message = exc.detail if isinstance(exc.detail, str) else "The request could not be completed."
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(code, message),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content=error_body("internal_error", "Something went wrong on our side. Please try again."),
        )
