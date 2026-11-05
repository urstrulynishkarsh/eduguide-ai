"""Claude, through the official Anthropic SDK.

* Structured output: `messages.parse(output_format=<Pydantic model>)` - the answer is validated
  against the schema by the SDK. Chat replies stream as text (`messages.stream`).
* Tiers map to a model (LLM_MODEL_*, else DEFAULT_MODELS) and an effort level. Thinking is adaptive
  (the default).
* Refusals: `fallbacks: "default"` lets the API retry a declined request on the model Anthropic
  recommends for that kind of refusal (on a stream too: already-sent text stays valid and the
  fallback model continues it); a final refusal becomes AIDeclinedError.
* The system prompt is the stable part of every request, so it is cached.
* The SDK retries rate limits, overload and network errors itself.

Logs carry the model, tier, token counts, latency and request id - never prompt or answer text.
"""

import logging
import time
from collections.abc import AsyncIterator, Iterator, Sequence
from contextlib import contextmanager
from typing import Any

import anthropic

from app.core import metrics
from app.llm.base import AIDeclinedError, AIUnavailableError, LLMResult, Message, ModelTier, RequestSize, T

logger = logging.getLogger(__name__)

DEFAULT_MODELS: dict[ModelTier, str] = {
    "fast": "claude-opus-5-5",
    "default": "claude-opus-5-5",
    "strong": "claude-opus-5-5",
}
_EFFORT: dict[ModelTier, str] = {"fast": "low", "default": "medium", "strong": "high"}
_FALLBACK_BETA = "server-side-fallback-2026-07-01"


@contextmanager
def _failures(tier: ModelTier) -> Iterator[None]:
    """Provider errors become AIUnavailableError; the reason goes to the log."""
    try:
        yield
    except (anthropic.AuthenticationError, anthropic.PermissionDeniedError):
        metrics.ai_call("anthropic", tier, "failed")
        logger.error("Claude rejected the API key - check ANTHROPIC_API_KEY in backend/.env")
        raise AIUnavailableError() from None
    except (anthropic.APIStatusError, anthropic.APIConnectionError) as exc:  # 429, 5xx, network
        metrics.ai_call("anthropic", tier, "failed")
        logger.warning("Claude request failed (%s, tier=%s)", type(exc).__name__, tier)
        raise AIUnavailableError() from None


def _log(response: Any, tier: ModelTier, started: float, request_id: str | None, outcome: str) -> None:
    usage = response.usage
    metrics.ai_call(
        "anthropic", tier, outcome, input_tokens=usage.input_tokens, output_tokens=usage.output_tokens
    )
    logger.info(
        "LLM %s tier=%s stop=%s in=%d cached=%d out=%d %.0f ms request=%s",
        response.model,
        tier,
        response.stop_reason,
        usage.input_tokens,
        usage.cache_read_input_tokens or 0,
        usage.output_tokens,
        (time.perf_counter() - started) * 1000,
        request_id,
    )


def _outcome(refused: bool, unusable: bool = False) -> str:
    return "declined" if refused else "invalid" if unusable else "ok"


class AnthropicProvider:
    request_size = RequestSize()

    def __init__(self, client: anthropic.AsyncAnthropic, models: dict[ModelTier, str]) -> None:
        self._client = client
        self._models = models

    def _request(
        self, system: str, messages: Sequence[Message], tier: ModelTier, max_output_tokens: int
    ) -> dict[str, Any]:
        """What every request carries, structured or streamed."""
        return {
            "model": self._models[tier],
            "max_tokens": max_output_tokens,
            "system": system,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "output_config": {"effort": _EFFORT[tier]},
            "cache_control": {"type": "ephemeral"},
            "betas": [_FALLBACK_BETA],
            "fallbacks": "default",
        }

    async def generate_structured(
        self,
        *,
        system: str,
        messages: Sequence[Message],
        schema: type[T],
        tier: ModelTier = "default",
        max_output_tokens: int = 16000,
    ) -> LLMResult[T]:
        started = time.perf_counter()
        with _failures(tier):
            response = await self._client.beta.messages.parse(
                **self._request(system, messages, tier, max_output_tokens), output_format=schema
            )
        refused, unusable = response.stop_reason == "refusal", response.parsed_output is None
        _log(response, tier, started, response._request_id, _outcome(refused, unusable))
        if refused:
            raise AIDeclinedError()
        if unusable:  # cut off (max_tokens) or not valid for the schema
            logger.warning("Claude gave no valid %s (stop=%s)", schema.__name__, response.stop_reason)
            raise AIUnavailableError()
        return LLMResult(
            output=response.parsed_output,
            model=response.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            latency_ms=(time.perf_counter() - started) * 1000,
        )

    async def stream_text(
        self,
        *,
        system: str,
        messages: Sequence[Message],
        tier: ModelTier = "default",
        max_output_tokens: int = 16000,
    ) -> AsyncIterator[str]:
        started = time.perf_counter()
        with _failures(tier):
            async with self._client.beta.messages.stream(
                **self._request(system, messages, tier, max_output_tokens)
            ) as stream:
                async for text in stream.text_stream:
                    yield text
                response = await stream.get_final_message()
        _log(response, tier, started, stream.request_id, _outcome(response.stop_reason == "refusal"))
        if response.stop_reason == "refusal":  # what was sent so far is discarded by the caller
            raise AIDeclinedError()
