"""Open models on Groq (https://console.groq.com), through the official Groq SDK.

* Structured output: `response_format` with a strict JSON schema, so the model can only write JSON
  of that shape (`strict_schema` turns the Pydantic model into the form strict mode needs). The
  answer is then validated by the same Pydantic model. Chat replies stream as text (`stream=True`).
* Tiers map to a model (LLM_MODEL_*, else DEFAULT_MODELS) and, for the gpt-oss models, a reasoning
  effort. The reasoning itself is not sent back: only the answer is used.
* Requests and replies are kept small. The free plan allows 8,000 tokens a minute, and Groq sizes
  each request as its input plus the largest reply of the last few minutes (measured; not in its
  docs). A request over 8,000 is refused outright (HTTP 413), so long replies make every later
  request too large. Hence `request_size` and `_MAX_REPLY_TOKENS`. The SDK waits out the per-minute
  limit itself (HTTP 429, Groq says how long); when the day's allowance is used up, people see the
  usual "busy, try again" and the log says why.
* Open models have no refusal signal, so AIDeclinedError is never raised here.

Logs carry the model, tier, token counts, latency and request id - never prompt or answer text.
"""

import logging
import time
from collections.abc import AsyncIterator, Iterator, Sequence
from contextlib import contextmanager
from typing import Any

import groq
from pydantic import BaseModel, ValidationError

from app.core import metrics
from app.llm.base import AIUnavailableError, LLMResult, Message, ModelTier, RequestSize, T

logger = logging.getLogger(__name__)

DEFAULT_MODELS: dict[ModelTier, str] = {
    "fast": "openai/gpt-oss-20b",
    "default": "openai/gpt-oss-120b",
    "strong": "openai/gpt-oss-120b",
}
_EFFORT: dict[ModelTier, str] = {"fast": "low", "default": "medium", "strong": "high"}
# Room for 3 questions with their reasoning (measured: up to 2,800 tokens) or a long explanation.
_MAX_REPLY_TOKENS = 3500


def strict_schema(model: type[BaseModel]) -> dict[str, Any]:
    """The model's JSON schema as strict mode needs it: every object lists all of its properties as
    required (optional ones are already "or null") and allows no others."""
    schema = model.model_json_schema()

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            if node.get("type") == "object" and "properties" in node:
                node["required"] = list(node["properties"])
                node["additionalProperties"] = False
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)

    visit(schema)
    return schema


@contextmanager
def _failures(tier: ModelTier, model: str) -> Iterator[None]:
    """Provider errors become AIUnavailableError; the reason goes to the log."""
    try:
        yield
    except (groq.APIStatusError, groq.APIConnectionError) as exc:
        metrics.ai_call("groq", tier, "failed")
        if isinstance(exc, groq.AuthenticationError | groq.PermissionDeniedError):
            logger.error("Groq rejected the API key - check GROQ_API_KEY in backend/.env")
        elif isinstance(exc, groq.NotFoundError):
            logger.error("Groq has no model %r - check LLM_MODEL_* in backend/.env", model)
        elif isinstance(exc, groq.APIStatusError):  # 429 and 413: the plan's limits; 5xx: Groq itself
            logger.warning("Groq request failed (HTTP %d, tier=%s): %s", exc.status_code, tier, exc.message)
        else:
            logger.warning("Groq could not be reached (tier=%s)", tier)
        raise AIUnavailableError() from None


class GroqProvider:
    # Writing 3 questions from 1,500 tokens of book text is about 3,900 tokens in, checking them about
    # 3,600: with a reply of up to 3,500, each stays under the free plan's 8,000.
    request_size = RequestSize(passage_tokens=1500, questions_per_call=3)

    def __init__(self, client: groq.AsyncGroq, models: dict[ModelTier, str]) -> None:
        self._client = client
        self._models = models

    def _request(
        self, system: str, messages: Sequence[Message], tier: ModelTier, max_output_tokens: int
    ) -> dict[str, Any]:
        """What every request carries, structured or streamed."""
        model = self._models[tier]
        # Only the gpt-oss models take these values; other models keep their own defaults.
        reasoning: dict[str, Any] = {}
        if model.startswith("openai/gpt-oss"):
            reasoning = {"reasoning_effort": _EFFORT[tier], "include_reasoning": False}
        return {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                *({"role": m.role, "content": m.content} for m in messages),
            ],
            "max_completion_tokens": min(max_output_tokens, _MAX_REPLY_TOKENS),
            **reasoning,
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
        request = self._request(system, messages, tier, max_output_tokens)
        started = time.perf_counter()
        with _failures(tier, request["model"]):
            response = await self._client.chat.completions.create(
                **request,
                response_format={
                    "type": "json_schema",
                    "json_schema": {"name": schema.__name__, "schema": strict_schema(schema), "strict": True},
                },
            )

        latency_ms = (time.perf_counter() - started) * 1000
        choice = response.choices[0]
        input_tokens = response.usage.prompt_tokens if response.usage else 0
        output_tokens = response.usage.completion_tokens if response.usage else 0
        logger.info(
            "LLM %s tier=%s finish=%s in=%d out=%d %.0f ms request=%s",
            response.model,
            tier,
            choice.finish_reason,
            input_tokens,
            output_tokens,
            latency_ms,
            response.id,
        )
        tokens = {"input_tokens": input_tokens, "output_tokens": output_tokens}
        try:
            output = schema.model_validate_json(choice.message.content or "")
        except ValidationError:  # cut off (length) or not valid for the model's rules
            metrics.ai_call("groq", tier, "invalid", **tokens)
            logger.warning("Groq gave no valid %s (finish=%s)", schema.__name__, choice.finish_reason)
            raise AIUnavailableError() from None
        metrics.ai_call("groq", tier, "ok", **tokens)
        return LLMResult(
            output=output,
            model=response.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
        )

    async def stream_text(
        self,
        *,
        system: str,
        messages: Sequence[Message],
        tier: ModelTier = "default",
        max_output_tokens: int = 16000,
    ) -> AsyncIterator[str]:
        request = self._request(system, messages, tier, max_output_tokens)
        started = time.perf_counter()
        finish, usage = None, None
        with _failures(tier, request["model"]):
            async for chunk in await self._client.chat.completions.create(**request, stream=True):
                usage = chunk.usage or (chunk.x_groq.usage if chunk.x_groq else None) or usage
                if not chunk.choices:
                    continue
                finish = chunk.choices[0].finish_reason or finish
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        input_tokens = usage.prompt_tokens if usage else 0
        output_tokens = usage.completion_tokens if usage else 0
        metrics.ai_call("groq", tier, "ok", input_tokens=input_tokens, output_tokens=output_tokens)
        logger.info(
            "LLM stream %s tier=%s finish=%s in=%d out=%d %.0f ms",
            request["model"],
            tier,
            finish,
            input_tokens,
            output_tokens,
            (time.perf_counter() - started) * 1000,
        )
