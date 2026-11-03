"""The Groq adapter: request shape, strict schemas, failures, and choosing the provider.
The SDK client is replaced by a stub."""

from types import SimpleNamespace
from typing import Any

import groq
import httpx
import pytest
from pydantic import BaseModel

import app.llm as llm
from app.core.config import Settings
from app.llm import AIUnavailableError, Message
from app.llm.groq_provider import DEFAULT_MODELS, GroqProvider, strict_schema
from app.question_generation.schemas import GeneratedBatch


class Answer(BaseModel):
    text: str
    note: str | None = None


def _response(content: str, finish_reason: str = "stop") -> SimpleNamespace:
    return SimpleNamespace(
        id="chatcmpl_1",
        model="openai/gpt-oss-120b",
        choices=[SimpleNamespace(finish_reason=finish_reason, message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(prompt_tokens=120, completion_tokens=30),
    )


class StubClient:
    def __init__(self, result: object) -> None:
        self.result = result
        self.calls: list[dict[str, Any]] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    async def _create(self, **kwargs: Any) -> object:
        self.calls.append(kwargs)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def _provider(result: object, **models: str) -> tuple[GroqProvider, StubClient]:
    client = StubClient(result)
    return GroqProvider(client, {**DEFAULT_MODELS, **models}), client  # type: ignore[arg-type]


async def _ask(provider: GroqProvider, tier: str = "default"):
    return await provider.generate_structured(
        system="rules",
        messages=[Message("user", "hi")],
        schema=Answer,
        tier=tier,  # type: ignore[arg-type]
    )


async def test_structured_answer_and_request_shape():
    provider, client = _provider(_response('{"text": "ok", "note": null}'))

    result = await _ask(provider, tier="fast")

    assert result.output == Answer(text="ok")
    assert (result.input_tokens, result.output_tokens) == (120, 30)
    request = client.calls[0]
    assert request["model"] == "openai/gpt-oss-20b"
    assert request["messages"] == [
        {"role": "system", "content": "rules"},
        {"role": "user", "content": "hi"},
    ]
    assert request["response_format"]["type"] == "json_schema"
    assert request["response_format"]["json_schema"]["strict"] is True
    assert request["response_format"]["json_schema"]["schema"]["additionalProperties"] is False
    assert (request["reasoning_effort"], request["include_reasoning"]) == ("low", False)
    assert request["max_completion_tokens"] == 3500  # long replies make later requests too large


async def test_models_other_than_gpt_oss_keep_their_own_reasoning_settings():
    provider, client = _provider(_response('{"text": "ok", "note": null}'), default="qwen/qwen3.8-27b")

    await _ask(provider)

    assert "reasoning_effort" not in client.calls[0] and "include_reasoning" not in client.calls[0]


def test_strict_schemas_close_every_object_and_keep_optional_fields_nullable():
    schema = strict_schema(GeneratedBatch)
    objects = [schema, *schema["$defs"].values()]
    objects = [node for node in objects if node.get("type") == "object"]

    assert len(objects) == 2  # the batch and the question
    for node in objects:
        assert node["additionalProperties"] is False
        assert node["required"] == list(node["properties"])
    question = schema["$defs"]["GeneratedQuestion"]["properties"]
    assert {"type": "null"} in question["case"]["anyOf"]


@pytest.mark.parametrize(
    ("content", "finish_reason"),
    [('{"text": "cut of', "length"), ('{"note": "no text"}', "stop")],
)
async def test_an_answer_that_is_cut_off_or_does_not_fit_is_not_used(content: str, finish_reason: str):
    provider, _ = _provider(_response(content, finish_reason))
    with pytest.raises(AIUnavailableError):
        await _ask(provider)


def _status_error(cls: type[groq.APIStatusError], status: int) -> groq.APIStatusError:
    response = httpx.Response(status, request=httpx.Request("POST", "https://api.groq.com/openai/v1/chat"))
    return cls("failed", response=response, body=None)


@pytest.mark.parametrize(
    "error",
    [
        _status_error(groq.AuthenticationError, 401),
        _status_error(groq.NotFoundError, 404),  # a model name Groq does not know
        _status_error(groq.APIStatusError, 413),  # larger than the plan allows per minute
        _status_error(groq.RateLimitError, 429),
        _status_error(groq.InternalServerError, 500),
        groq.APIConnectionError(request=httpx.Request("POST", "https://api.groq.com/openai/v1/chat")),
    ],
)
async def test_provider_failures_become_ai_unavailable(error: Exception):
    provider, _ = _provider(error)
    with pytest.raises(AIUnavailableError):
        await _ask(provider)


def test_groq_is_chosen_with_its_own_models_unless_a_tier_is_set(monkeypatch: pytest.MonkeyPatch):
    settings = Settings(
        _env_file=None,
        jwt_secret_key="s" * 48,
        llm_provider="groq",
        groq_api_key="gsk_test",
        llm_model_strong="qwen/qwen3.8-27b",
    )
    monkeypatch.setattr(llm, "get_settings", lambda: settings)
    llm._provider.cache_clear()
    try:
        provider = llm.get_llm_provider()
    finally:
        llm._provider.cache_clear()

    assert isinstance(provider, GroqProvider)
    assert provider._models == {
        "fast": "openai/gpt-oss-20b",
        "default": "openai/gpt-oss-120b",
        "strong": "qwen/qwen3.8-27b",
    }
