"""Learn a concept: "Explain this" from the child's own books (spec §21, §42)."""

import uuid
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

from app.rag.answering import ExplainStyle
from app.schemas.library import Source


class ExplainRequest(BaseModel):
    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=1000)]
    student_id: uuid.UUID | None = Field(
        default=None, description="Which child (parents only). A student session always uses itself."
    )
    book_id: uuid.UUID | None = Field(default=None, description="Look only in this book.")
    chapter_id: uuid.UUID | None = Field(default=None, description="Look only in this chapter.")
    style: ExplainStyle = Field(
        default="normal",
        description="normal · simple · like_10 (Explain like I'm 10) · hindi · hinglish",
    )


class ExplainResponse(BaseModel):
    explanation: str
    steps: list[str]
    style: ExplainStyle
    origin: Literal["generated"] = Field(
        default="generated", description="Written by the AI from the sources - not a quote from the book."
    )
    sources: list[Source] = Field(description='Shown as "Based on: …". Never empty.')
