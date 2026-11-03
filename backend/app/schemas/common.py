"""Schemas shared by several endpoints."""

from typing import Any

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Any | None = None


class ErrorResponse(BaseModel):
    """The shape of every error the API returns."""

    error: ErrorDetail


class OptionItem(BaseModel):
    """One choice in a dropdown: a stable code plus the text to show."""

    code: str
    label: str
