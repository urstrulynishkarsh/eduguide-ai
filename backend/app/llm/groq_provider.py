"""Open models on Groq (https://console.groq.com), through the official Groq SDK. Groq speaks
OpenAI's chat-completions format, so OpenAICompatibleProvider does the work (structured output,
streaming, failures); this file holds what is Groq's own.

* Tiers map to a model (LLM_MODEL_*, else DEFAULT_MODELS) and, for the gpt-oss models, a reasoning
  effort. The reasoning itself is not sent back: only the answer is used.
* Requests and replies are kept small. The free plan allows 8,000 tokens a minute, and Groq sizes
  each request as its input plus the largest reply of the last few minutes (measured; not in its
  docs). A request over 8,000 is refused outright (HTTP 413), so long replies make every later
  request too large. Hence `request_size` and `max_reply_tokens`. The SDK waits out the per-minute
  limit itself (HTTP 429, Groq says how long); when the day's allowance is used up, people see the
  usual "busy, try again" and the log says why.
"""

from typing import Any

import groq

from app.llm.base import ModelTier, RequestSize
from app.llm.openai_compatible_provider import OpenAICompatibleProvider

DEFAULT_MODELS: dict[ModelTier, str] = {
    "fast": "openai/gpt-oss-20b",
    "default": "openai/gpt-oss-120b",
    "strong": "openai/gpt-oss-120b",
}
_EFFORT: dict[ModelTier, str] = {"fast": "low", "default": "medium", "strong": "high"}


class GroqProvider(OpenAICompatibleProvider):
    name = "groq"
    sdk = groq
    # Writing 3 questions from 1,500 tokens of book text is about 3,900 tokens in, checking them about
    # 3,600: with a reply of up to 3,500, each stays under the free plan's 8,000.
    request_size = RequestSize(passage_tokens=1500, questions_per_call=3)
    # Room for 3 questions with their reasoning (measured: up to 2,800 tokens) or a long explanation.
    max_reply_tokens = 3500

    def _extras(self, model: str, tier: ModelTier, *, stream: bool) -> dict[str, Any]:
        # Only the gpt-oss models take these values; other models keep their own defaults.
        if model.startswith("openai/gpt-oss"):
            return {"reasoning_effort": _EFFORT[tier], "include_reasoning": False}
        return {}

    @staticmethod
    def _stream_usage(chunk: Any) -> Any:
        return chunk.usage or (chunk.x_groq.usage if chunk.x_groq else None)
