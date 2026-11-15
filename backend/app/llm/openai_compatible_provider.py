"""Any service that speaks OpenAI's chat-completions format, through the official OpenAI SDK
(LLM_PROVIDER=openai_compatible: the address, the key and the model come from backend/.env).
Groq speaks the same format, so its adapter (groq_provider.py) builds on this one.

* Structured output: `response_format` with a strict JSON schema, so the model can only write JSON
  of that shape (`strict_schema` turns the Pydantic model into the form strict mode needs). The
  answer is then validated by the same Pydantic model. Chat replies stream as text (`stream=True`).
* Not every service keeps to the format for every model: some drop `response_format` or the system
  prompt. `pytest -m live` shows whether the chosen model keeps both.
* There is no refusal signal to rely on, so AIDeclinedError is never raised here.

Logs carry the model, tier, token counts, latency and request id - never prompt or answer text.
"""

import logging
import time
from collections.abc import AsyncIterator, Iterator, Sequence
from contextlib import contextmanager
from types import ModuleType
from typing import Any

import openai
from pydantic import BaseModel, ValidationError

from app.core import metrics
from app.llm.base import AIUnavailableError, LLMResult, Message, ModelTier, RequestSize, T

logger = logging.getLogger(__name__)


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


class OpenAICompatibleProvider:
    name = "openai_compatible"  # the LLM_PROVIDER value; also in the metrics and the logs
    sdk: ModuleType = openai  # the SDK whose errors the client raises
    request_size = RequestSize()
    max_reply_tokens: int | None = None  # a cap on every reply, where a plan needs one

    def __init__(self, client: Any, models: dict[ModelTier, str]) -> None:
        """`client`: an `openai.AsyncOpenAI`, or another SDK's client of the same shape."""
        self._client = client
        self._models = models

    def _extras(self, model: str, tier: ModelTier, *, stream: bool) -> dict[str, Any]:
        """What only this service takes. Here: a stream ends with its token counts."""
        return {"stream_options": {"include_usage": True}} if stream else {}

    @staticmethod
    def _stream_usage(chunk: Any) -> Any:
        """The token counts on a streamed chunk, if it carries them."""
        return chunk.usage

    @contextmanager
    def _failures(self, tier: ModelTier, model: str) -> Iterator[None]:
        """Provider errors become AIUnavailableError; the reason goes to the log."""
        sdk = self.sdk
        try:
            yield
        except (sdk.APIStatusError, sdk.APIConnectionError) as exc:
            metrics.ai_call(self.name, tier, "failed")
            if isinstance(exc, sdk.AuthenticationError | sdk.PermissionDeniedError):
                key = f"{self.name.upper()}_API_KEY"
                logger.error("%s rejected the API key - check %s in backend/.env", self.name, key)
            elif isinstance(exc, sdk.NotFoundError):
                logger.error("%s has no model %r - check LLM_MODEL_* in backend/.env", self.name, model)
            elif isinstance(exc, sdk.APIStatusError):  # 429 and 413: the plan's limits; 5xx: the service
                logger.warning(
                    "%s request failed (HTTP %d, tier=%s): %s", self.name, exc.status_code, tier, exc.message
                )
            else:
                logger.warning("%s could not be reached (tier=%s)", self.name, tier)
            raise AIUnavailableError() from None

    def _request(
        self,
        system: str,
        messages: Sequence[Message],
        tier: ModelTier,
        max_output_tokens: int,
        *,
        stream: bool = False,
    ) -> dict[str, Any]:
        """What every request carries, structured or streamed."""
        model = self._models[tier]
        return {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                *({"role": m.role, "content": m.content} for m in messages),
            ],
            "max_completion_tokens": min(max_output_tokens, self.max_reply_tokens or max_output_tokens),
            **self._extras(model, tier, stream=stream),
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
        with self._failures(tier, request["model"]):
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
            metrics.ai_call(self.name, tier, "invalid", **tokens)
            logger.warning(
                "%s gave no valid %s (finish=%s)", self.name, schema.__name__, choice.finish_reason
            )
            raise AIUnavailableError() from None
        metrics.ai_call(self.name, tier, "ok", **tokens)
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
        request = self._request(system, messages, tier, max_output_tokens, stream=True)
        started = time.perf_counter()
        finish, usage = None, None
        with self._failures(tier, request["model"]):
            async for chunk in await self._client.chat.completions.create(**request, stream=True):
                usage = self._stream_usage(chunk) or usage
                if not chunk.choices:
                    continue
                finish = chunk.choices[0].finish_reason or finish
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        input_tokens = usage.prompt_tokens if usage else 0
        output_tokens = usage.completion_tokens if usage else 0
        metrics.ai_call(self.name, tier, "ok", input_tokens=input_tokens, output_tokens=output_tokens)
        logger.info(
            "LLM stream %s tier=%s finish=%s in=%d out=%d %.0f ms",
            request["model"],
            tier,
            finish,
            input_tokens,
            output_tokens,
            (time.perf_counter() - started) * 1000,
        )
