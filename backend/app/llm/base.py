"""The provider-neutral interface to language models (docs/06-llm-interfaces.md).

Business code imports only from here. Every answer is parsed into a Pydantic model before
anyone uses it; free text is never trusted as structured data.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Generic, Literal, Protocol, TypeVar

from pydantic import BaseModel

from app.core.errors import AppError

T = TypeVar("T", bound=BaseModel)

# fast: small jobs (understanding a question) · default: writing explanations and questions ·
# strong: the hardest checks.
ModelTier = Literal["fast", "default", "strong"]


@dataclass(frozen=True, slots=True)
class Message:
    role: Literal["user", "assistant"]
    content: str


@dataclass(frozen=True, slots=True)
class RequestSize:
    """How much one request to a provider may carry when writing practice questions."""

    passage_tokens: int = 6000  # book text given to the question writer and to its reviewer
    questions_per_call: int = 10  # questions written, and then reviewed, in one request


@dataclass(frozen=True, slots=True)
class LLMResult(Generic[T]):
    output: T
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: float


class LLMProvider(Protocol):
    request_size: RequestSize

    async def generate_structured(
        self,
        *,
        system: str,
        messages: Sequence[Message],
        schema: type[T],
        tier: ModelTier = "default",
        max_output_tokens: int = 16000,
    ) -> LLMResult[T]: ...


class AINotConfiguredError(AppError):
    status_code = 503
    code = "ai_not_configured"
    message = "The AI features are not switched on yet."


class AIUnavailableError(AppError):
    """The provider failed (busy, network, bad key). Logged in detail; the person sees this."""

    status_code = 503
    code = "ai_unavailable"
    message = "The AI tutor is busy right now. Please try again in a minute."


class AIDeclinedError(AppError):
    """The model declined the request (a safety refusal)."""

    status_code = 422
    code = "ai_declined"
    message = "I can't help with that one. Please ask about something from your books."
