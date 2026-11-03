"""The Claude adapter: request shape, refusals, failures. The SDK client is replaced by a stub."""

from types import SimpleNamespace

import anthropic
import httpx2
import pytest
from pydantic import BaseModel

from app.llm import AIDeclinedError, AIUnavailableError, Message
from app.llm.anthropic_provider import AnthropicProvider


class Answer(BaseModel):
    text: str


def _response(parsed: Answer | None, stop_reason: str = "end_turn") -> SimpleNamespace:
    usage = SimpleNamespace(input_tokens=120, output_tokens=30, cache_read_input_tokens=100)
    return SimpleNamespace(
        parsed_output=parsed,
        stop_reason=stop_reason,
        usage=usage,
        model="claude-opus-5-5",
        _request_id="req_1",
    )


class StubStream:
    """What `client.beta.messages.stream(...)` gives inside `async with`."""

    request_id = "req_2"

    def __init__(self, result: object, pieces: list[str]) -> None:
        self.result = result
        self.pieces = pieces

    async def __aenter__(self) -> "StubStream":
        if isinstance(self.result, Exception):  # the request is sent on entering
            raise self.result
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    @property
    async def text_stream(self):
        for piece in self.pieces:
            yield piece

    async def get_final_message(self) -> object:
        return self.result


class StubClient:
    def __init__(self, result: object, pieces: list[str] | None = None) -> None:
        self.result = result
        self.pieces = pieces or []
        self.calls: list[dict] = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(parse=self._parse, stream=self._stream))

    async def _parse(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result

    def _stream(self, **kwargs: object) -> StubStream:
        self.calls.append(kwargs)
        return StubStream(self.result, self.pieces)


def _provider(result: object, pieces: list[str] | None = None) -> tuple[AnthropicProvider, StubClient]:
    client = StubClient(result, pieces)
    models = {"fast": "claude-haiku-5-5", "default": "claude-opus-5-5", "strong": "claude-opus-5-5"}
    return AnthropicProvider(client, models), client  # type: ignore[arg-type]


async def _ask(provider: AnthropicProvider, tier: str = "default"):
    return await provider.generate_structured(
        system="rules",
        messages=[Message("user", "hi")],
        schema=Answer,
        tier=tier,  # type: ignore[arg-type]
    )


async def test_structured_answer_and_request_shape():
    provider, client = _provider(_response(Answer(text="ok")))

    result = await _ask(provider, tier="fast")

    assert result.output == Answer(text="ok")
    assert (result.input_tokens, result.output_tokens) == (120, 30)
    request = client.calls[0]
    assert request["model"] == "claude-haiku-5-5"
    assert request["output_format"] is Answer
    assert request["output_config"] == {"effort": "low"}
    assert request["fallbacks"] == "default"
    assert request["betas"] == ["server-side-fallback-2026-07-01"]
    assert request["cache_control"] == {"type": "ephemeral"}
    assert request["messages"] == [{"role": "user", "content": "hi"}]
    assert "temperature" not in request


async def test_refusal_becomes_a_friendly_decline():
    provider, _ = _provider(_response(None, stop_reason="refusal"))
    with pytest.raises(AIDeclinedError):
        await _ask(provider)


async def test_cut_off_answer_is_not_used():
    provider, _ = _provider(_response(None, stop_reason="max_tokens"))
    with pytest.raises(AIUnavailableError):
        await _ask(provider)


def _status_error(cls: type[anthropic.APIStatusError], status: int) -> anthropic.APIStatusError:
    response = httpx2.Response(
        status, request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    )
    return cls("failed", response=response, body=None)


@pytest.mark.parametrize(
    "error",
    [
        _status_error(anthropic.AuthenticationError, 401),
        _status_error(anthropic.RateLimitError, 429),
        _status_error(anthropic.InternalServerError, 500),
        anthropic.APIConnectionError(request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages")),
    ],
)
async def test_provider_failures_become_ai_unavailable(error: Exception):
    provider, _ = _provider(error)
    with pytest.raises(AIUnavailableError):
        await _ask(provider)


async def _streamed(provider: AnthropicProvider, received: list[str]) -> None:
    async for piece in provider.stream_text(system="rules", messages=[Message("user", "hi")]):
        received.append(piece)


async def test_a_streamed_reply_arrives_piece_by_piece_with_the_same_settings():
    provider, client = _provider(_response(None), pieces=["Pehle ", "dono taraf ", "4 ghatao."])

    received: list[str] = []
    await _streamed(provider, received)

    assert received == ["Pehle ", "dono taraf ", "4 ghatao."]
    request = client.calls[0]
    assert (request["model"], request["output_config"]) == ("claude-opus-5-5", {"effort": "medium"})
    assert (request["fallbacks"], request["cache_control"]) == ("default", {"type": "ephemeral"})
    assert request["system"] == "rules" and "output_format" not in request


async def test_a_streamed_refusal_is_raised_after_what_was_sent():
    provider, _ = _provider(_response(None, stop_reason="refusal"), pieces=["Let me"])
    received: list[str] = []
    with pytest.raises(AIDeclinedError):
        await _streamed(provider, received)
    assert received == ["Let me"]  # the caller discards it


async def test_a_failed_stream_becomes_ai_unavailable():
    provider, _ = _provider(_status_error(anthropic.RateLimitError, 429))
    with pytest.raises(AIUnavailableError):
        await _streamed(provider, [])
