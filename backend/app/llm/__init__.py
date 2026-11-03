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
    RequestSize,
)

__all__ = [
    "AIDeclinedError",
    "AINotConfiguredError",
    "AIUnavailableError",
    "LLMProvider",
    "LLMResult",
    "Message",
    "ModelTier",
    "RequestSize",
    "get_llm_provider",
]


@lru_cache
def _provider() -> LLMProvider | None:
    settings = get_settings()
    chosen: dict[ModelTier, str] = {
        "fast": settings.llm_model_fast,
        "default": settings.llm_model_default,
        "strong": settings.llm_model_strong,
    }
    if settings.llm_provider == "anthropic":
        import anthropic

        from app.llm.anthropic_provider import DEFAULT_MODELS, AnthropicProvider

        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key, max_retries=3, timeout=120)
        return AnthropicProvider(client, _models(chosen, DEFAULT_MODELS))
    if settings.llm_provider == "groq":
        import groq

        from app.llm.groq_provider import DEFAULT_MODELS as GROQ_MODELS
        from app.llm.groq_provider import GroqProvider

        return GroqProvider(
            # More retries: on the free plan they wait out the per-minute limit (Groq says how long).
            groq.AsyncGroq(api_key=settings.groq_api_key, max_retries=6, timeout=120),
            _models(chosen, GROQ_MODELS),
        )
    return None


def _models(chosen: dict[ModelTier, str], defaults: dict[ModelTier, str]) -> dict[ModelTier, str]:
    """The model of each tier: the one set in backend/.env, else the provider's default."""
    return {tier: chosen[tier] or defaults[tier] for tier in defaults}


def get_llm_provider() -> LLMProvider:
    """The configured provider. Raises AINotConfiguredError (503) when AI is switched off."""
    provider = _provider()
    if provider is None:
        raise AINotConfiguredError()
    return provider
