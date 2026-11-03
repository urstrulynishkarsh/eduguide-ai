"""Open models on Groq (https://console.groq.com), through the official Groq SDK.

* Structured output: `response_format` with a strict JSON schema, so the model can only write JSON
  of that shape (`strict_schema` turns the Pydantic model into the form strict mode needs). The
  answer is then validated by the same Pydantic model.
* Tiers map to a model (LLM_MODEL_*, else DEFAULT_MODELS) and, for the gpt-oss models, a reasoning
  effort. The reasoning itself is not sent back: only the answer is used.
* The SDK retries rate limits and network errors itself. Groq's free plan allows only a few
  thousand tokens a minute and a limited number a day; when they are used up, people see the usual
  "busy, try again" and the log says why.
* Open models have no refusal signal, so AIDeclinedError is never raised here.

Logs carry the model, tier, token counts, latency and request id - never prompt or answer text.
"""

import logging
import time
from collections.abc import Sequence
from typing import Any

import groq
from pydantic import BaseModel, ValidationError

from app.llm.base import AIUnavailableError, LLMResult, Message, ModelTier, T

logger = logging.getLogger(__name__)

DEFAULT_MODELS: dict[ModelTier, str] = {
    "fast": "openai/gpt-oss-20b",
    "default": "openai/gpt-oss-120b",
    "strong": "openai/gpt-oss-120b",
}
_EFFORT: dict[ModelTier, str] = {"fast": "low", "default": "medium", "strong": "high"}


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


class GroqProvider:
    def __init__(self, client: groq.AsyncGroq, models: dict[ModelTier, str]) -> None:
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
        # Only the gpt-oss models take these values; other models keep their own defaults.
        reasoning: dict[str, Any] = {}
        if model.startswith("openai/gpt-oss"):
            reasoning = {"reasoning_effort": _EFFORT[tier], "include_reasoning": False}
        started = time.perf_counter()
        try:
            response = await self._client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    *({"role": m.role, "content": m.content} for m in messages),
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {"name": schema.__name__, "schema": strict_schema(schema), "strict": True},
                },
                max_completion_tokens=max_output_tokens,
                **reasoning,
            )
        except (groq.AuthenticationError, groq.PermissionDeniedError):
            logger.error("Groq rejected the API key - check GROQ_API_KEY in backend/.env")
            raise AIUnavailableError() from None
        except groq.NotFoundError:
            logger.error("Groq has no model %r - check LLM_MODEL_* in backend/.env", model)
            raise AIUnavailableError() from None
        except groq.APIStatusError as exc:  # 429 and 413: the plan's limits; 5xx: Groq itself
            logger.warning("Groq request failed (HTTP %d, tier=%s): %s", exc.status_code, tier, exc.message)
            raise AIUnavailableError() from None
        except groq.APIConnectionError:
            logger.warning("Groq could not be reached (tier=%s)", tier)
            raise AIUnavailableError() from None

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
        try:
            output = schema.model_validate_json(choice.message.content or "")
        except ValidationError:  # cut off (length) or not valid for the model's rules
            logger.warning("Groq gave no valid %s (finish=%s)", schema.__name__, choice.finish_reason)
            raise AIUnavailableError() from None
        return LLMResult(
            output=output,
            model=response.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
        )
