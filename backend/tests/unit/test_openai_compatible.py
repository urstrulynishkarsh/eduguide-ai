"""The adapter for any service in OpenAI's format, where it differs from Groq's (test_groq.py covers
what they share): what a request carries, token counts on a stream, failures, and choosing the
provider. The SDK client is replaced by a stub."""

from types import SimpleNamespace

import httpx
import openai
import pytest
from pydantic import BaseModel

import app.llm as llm
from app.core import metrics
from app.core.config import Settings
from app.llm import AIUnavailableError, Message
from app.llm.openai_compatible_provider import OpenAICompatibleProvider
from tests.fakes import ChatCompletionsStub, chat_completion

MODELS = {"fast": "model-small", "default": "model-a", "strong": "model-a"}


class Answer(BaseModel):
    text: str


def _provider(result: object) -> tuple[OpenAICompatibleProvider, ChatCompletionsStub]:
    client = ChatCompletionsStub(result)
    return OpenAICompatibleProvider(client, MODELS), client  # type: ignore[arg-type]


async def _ask(provider: OpenAICompatibleProvider):
    return await provider.generate_structured(
        system="rules", messages=[Message("user", "hi")], schema=Answer, tier="fast"
    )


async def test_a_request_keeps_the_full_reply_size_and_adds_nothing_of_groqs():
    provider, client = _provider(chat_completion('{"text": "ok"}'))

    result = await _ask(provider)

    assert result.output == Answer(text="ok")
    request = client.calls[0]
    assert request["model"] == "model-small"
    assert request["max_completion_tokens"] == 16000
    assert request["response_format"]["json_schema"]["strict"] is True
    assert not {"reasoning_effort", "include_reasoning", "stream_options"} & request.keys()


async def test_a_stream_asks_for_its_token_counts_and_reports_them(monkeypatch: pytest.MonkeyPatch):
    def chunk(content: str | None, usage: object = None) -> SimpleNamespace:
        choice = SimpleNamespace(delta=SimpleNamespace(content=content), finish_reason=None)
        return SimpleNamespace(choices=[choice], usage=usage)

    usage = SimpleNamespace(prompt_tokens=200, completion_tokens=12)
    provider, client = _provider([chunk("Pehle "), chunk("4 ghatao."), chunk(None, usage)])
    counted: list[tuple] = []
    monkeypatch.setattr(metrics, "ai_call", lambda *labels, **tokens: counted.append((labels, tokens)))

    received = [
        piece async for piece in provider.stream_text(system="rules", messages=[Message("user", "hi")])
    ]

    assert received == ["Pehle ", "4 ghatao."]
    assert client.calls[0]["stream"] is True
    assert client.calls[0]["stream_options"] == {"include_usage": True}
    assert counted == [(("openai_compatible", "default", "ok"), {"input_tokens": 200, "output_tokens": 12})]


def _status_error(cls: type[openai.APIStatusError], status: int) -> openai.APIStatusError:
    response = httpx.Response(status, request=httpx.Request("POST", "https://llm.example.com/v1/chat"))
    return cls("failed", response=response, body=None)


@pytest.mark.parametrize(
    "error",
    [
        _status_error(openai.AuthenticationError, 401),
        _status_error(openai.NotFoundError, 404),  # a model name the service does not know
        _status_error(openai.RateLimitError, 429),
        _status_error(openai.InternalServerError, 500),
        openai.APIConnectionError(request=httpx.Request("POST", "https://llm.example.com/v1/chat")),
    ],
)
async def test_provider_failures_become_ai_unavailable(error: Exception):
    provider, _ = _provider(error)
    with pytest.raises(AIUnavailableError):
        await _ask(provider)


def test_it_is_chosen_with_its_address_and_the_default_model_for_an_empty_tier(
    monkeypatch: pytest.MonkeyPatch,
):
    settings = Settings(
        _env_file=None,
        jwt_secret_key="s" * 48,
        llm_provider="openai_compatible",
        openai_compatible_base_url="https://llm.example.com/v1",
        openai_compatible_api_key="sk-test",
        llm_model_default="model-a",
        llm_model_fast="model-small",
    )
    monkeypatch.setattr(llm, "get_settings", lambda: settings)
    llm._provider.cache_clear()
    try:
        provider = llm.get_llm_provider()
    finally:
        llm._provider.cache_clear()

    assert type(provider) is OpenAICompatibleProvider
    assert provider._models == MODELS
    assert str(provider._client.base_url) == "https://llm.example.com/v1/"
