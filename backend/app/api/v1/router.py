"""Collects every v1 route. New feature areas are added here step by step."""

from fastapi import APIRouter

from app.api.v1 import auth, books, chapters, documents, meta, students
from app.schemas.common import ErrorResponse

api_v1_router = APIRouter(
    # Tell the API docs that every error uses our error format.
    responses={
        401: {"model": ErrorResponse, "description": "Not signed in, or the session expired"},
        403: {"model": ErrorResponse, "description": "Signed in, but not allowed to do this"},
        404: {"model": ErrorResponse, "description": "Not found (or not yours)"},
        422: {"model": ErrorResponse, "description": "Some of the information sent is not valid"},
    }
)
api_v1_router.include_router(auth.router)
api_v1_router.include_router(students.router)
api_v1_router.include_router(books.router)
api_v1_router.include_router(documents.router)
api_v1_router.include_router(chapters.router)
api_v1_router.include_router(meta.router)
