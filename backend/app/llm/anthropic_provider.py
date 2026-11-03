"""Claude, through the official Anthropic SDK.

* Structured output: `messages.parse(output_format=<Pydantic model>)` - the answer is validated
  against the schema by the SDK.
* Tiers map to a model (LLM_MODEL_*, else DEFAULT_MODELS) and an effort level. Thinking is adaptive
  (the default).
* Refusals: `fallbacks: "default"` lets the API retry a declined request on the model Anthropic
  recommends for that kind of refusal; a final refusal becomes AIDeclinedError.
* The system prompt is the stable part of every request, so it is cached.
* The SDK retries rate limits, overload and network errors itself.

Logs carry the model, tier, token counts, latency and request id - never prompt or answer text.
"""

import logging
import time
from collections.abc import Sequence

import anthropic

from app.llm.base import AIDeclinedError, AIUnavailableError, LLMResult, Message, ModelTier, RequestSize, T

logger = logging.getLogger(__name__)

DEFAULT_MODELS: dict[ModelTier, str] = {
    "fast": "claude-opus-5-5",
    "default": "claude-opus-5-5",
    "strong": "claude-opus-5-5",
}
_EFFORT: dict[ModelTier, str] = {"fast": "low", "default": "medium", "strong": "high"}
_FALLBACK_BETA = "server-side-fallback-2026-07-01"


class AnthropicProvider:
    request_size = RequestSize()

    def __init__(self, client: anthropic.AsyncAnthropic, models: dict[ModelTier, str]) -> None:
        self._client = client
        self._models = models

    async def generate_structured(
        self,
        *,
        system: str,
        messages: Sequence[Message],
        schema: type[T],
        tier: ModelTier = "default",
        max_output_tokens: int = 16000,
    ) -> LLMResult[T]:
        model = self._models[tier]
        started = time.perf_counter()
        try:
            response = await self._client.beta.messages.parse(
                model=model,
                max_tokens=max_output_tokens,
                system=system,
                messages=[{"role": m.role, "content": m.content} for m in messages],
                output_format=schema,
                output_config={"effort": _EFFORT[tier]},
                cache_control={"type": "ephemeral"},
                betas=[_FALLBACK_BETA],
                fallbacks="default",
            )
        except (anthropic.AuthenticationError, anthropic.PermissionDeniedError):
            logger.error("Claude rejected the API key - check ANTHROPIC_API_KEY in backend/.env")
            raise AIUnavailableError() from None
        except (anthropic.APIStatusError, anthropic.APIConnectionError) as exc:  # 429, 5xx, network
            logger.warning("Claude request failed (%s, tier=%s)", type(exc).__name__, tier)
            raise AIUnavailableError() from None

        latency_ms = (time.perf_counter() - started) * 1000
        usage = response.usage
        logger.info(
            "LLM %s tier=%s stop=%s in=%d cached=%d out=%d %.0f ms request=%s",
            response.model,
            tier,
            response.stop_reason,
            usage.input_tokens,
            usage.cache_read_input_tokens or 0,
            usage.output_tokens,
            latency_ms,
            response._request_id,
        )
        if response.stop_reason == "refusal":
            raise AIDeclinedError()
        if response.parsed_output is None:  # cut off (max_tokens) or not valid for the schema
            logger.warning("Claude gave no valid %s (stop=%s)", schema.__name__, response.stop_reason)
            raise AIUnavailableError()
        return LLMResult(
            output=response.parsed_output,
            model=response.model,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            latency_ms=latency_ms,
        )
