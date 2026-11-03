"""One interface to language models; the provider is chosen with LLM_PROVIDER.

Design: docs/06-llm-interfaces.md. Business code calls `get_llm_provider()` and the
`LLMProvider` interface - never a vendor SDK.
"""

from functools import lru_cache

from app.core.config import get_settings
from app.llm.base import (
    AIDeclinedError,
    AINotConfiguredError,
    AIUnavailableError,
    LLMProvider,
    LLMResult,
    Message,
    ModelTier,
)

__all__ = [
    "AIDeclinedError",
    "AINotConfiguredError",
    "AIUnavailableError",
    "LLMProvider",
    "LLMResult",
    "Message",
    "ModelTier",
    "get_llm_provider",
]


@lru_cache
def _provider() -> LLMProvider | None:
    settings = get_settings()
    if settings.llm_provider == "none":
        return None
    import anthropic

    from app.llm.anthropic_provider import AnthropicProvider

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key, max_retries=3, timeout=120)
    return AnthropicProvider(
        client,
        {
            "fast": settings.llm_model_fast,
            "default": settings.llm_model_default,
            "strong": settings.llm_model_strong,
        },
    )


def get_llm_provider() -> LLMProvider:
    """The configured provider. Raises AINotConfiguredError (503) when AI is switched off."""
    provider = _provider()
    if provider is None:
        raise AINotConfiguredError()
    return provider
