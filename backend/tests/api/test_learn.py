"""POST /learn/explain: answers only from the child's books, with sources, or says it can't."""

import re

import pytest
from httpx import AsyncClient

from app import llm
from app.rag.answering import Explanation, QueryUnderstanding
from tests.api.helpers import API, add_child, create_book, error_code, register, start_child_session, upload
from tests.fakes import FakeLLM
from tests.samples import make_pdf


@pytest.fixture
def fake_llm(monkeypatch: pytest.MonkeyPatch):
    def install(*outputs) -> FakeLLM:
        fake = FakeLLM(*outputs)
        monkeypatch.setattr(llm, "get_llm_provider", lambda: fake)
        return fake

    return install


def _understood(query: str = "how to solve a linear equation 2x + 4 = 10", on_topic: bool = True):
    return QueryUnderstanding(on_topic=on_topic, search_query=query)


def _explained(**overrides) -> Explanation:
    values = {
        "enough_information": True,
        "explanation": "Subtract 4 from both sides, then divide by 2.",
        "steps": ["2x = 6", "x = 3"],
        "sources_used": ["S1"],
    }
    return Explanation(**{**values, **overrides})


async def _family_with_book(client: AsyncClient):
    parent = await register(client)
    child = await add_child(client, parent, class_level="class_8")
    book = await create_book(client, parent.headers, student_id=child["id"], class_level=None)
    await upload(client, parent.headers, book["id"], make_pdf())
    return parent, child, book


async def test_ai_switched_off_is_a_clear_503(client: AsyncClient):
    parent = await register(client)
    response = await client.post(
        f"{API}/learn/explain", json={"question": "What is x?"}, headers=parent.headers
    )
    assert response.status_code == 503
    assert error_code(response) == "ai_not_configured"


class CitingFakeLLM(FakeLLM):
    """Cites the passage that holds the worked example, wherever retrieval placed it."""

    async def generate_structured(self, **request):
        if request["schema"] is Explanation:
            prompt = request["messages"][0].content
            tag = re.search(r'<passage tag="(S\d+)"[^>]*>\nExample 2:', prompt).group(1)
            self.outputs.append(_explained(sources_used=[tag]))
        return await super().generate_structured(**request)


async def test_explain_from_the_childs_book_with_sources(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    parent, child, book = await _family_with_book(client)
    fake = CitingFakeLLM(_understood())
    monkeypatch.setattr(llm, "get_llm_provider", lambda: fake)

    response = await client.post(
        f"{API}/learn/explain",
        json={"question": "2x + 4 = 10 kaise solve karein?", "student_id": child["id"], "style": "hinglish"},
        headers=parent.headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["explanation"] == "Subtract 4 from both sides, then divide by 2."
    assert body["origin"] == "generated"
    assert body["style"] == "hinglish"
    assert len(body["sources"]) == 1
    source = body["sources"][0]
    assert source["book_id"] == book["id"]
    assert source["chapter"] == "Chapter 2 Linear Equations in One Variable"
    assert source["page"] == 3

    understand, explain = fake.requests
    assert understand["tier"] == "fast"
    assert explain["schema"] is Explanation
    assert "Class 8" in explain["system"]
    assert "Write in Hinglish" in explain["messages"][0].content
    assert "Example 2: Solve 2x + 4 = 10." in explain["messages"][0].content  # the passage reached the model


async def test_nothing_in_the_books_means_insufficient_context(client: AsyncClient, fake_llm):
    parent = await register(client)
    child = await add_child(client, parent)
    fake = fake_llm(_understood("photosynthesis in plants"))

    response = await client.post(
        f"{API}/learn/explain",
        json={"question": "What is photosynthesis?", "student_id": child["id"]},
        headers=parent.headers,
    )

    assert response.status_code == 422
    assert error_code(response) == "insufficient_context"
    assert "couldn't find enough information" in response.json()["error"]["message"]
    assert len(fake.requests) == 1  # the explanation was never asked for


async def test_off_topic_and_ungrounded_answers_are_refused(client: AsyncClient, fake_llm):
    parent, child, _ = await _family_with_book(client)
    payload = {"question": "Who won the cricket match?", "student_id": child["id"]}

    fake_llm(_understood(on_topic=False))
    off_topic = await client.post(f"{API}/learn/explain", json=payload, headers=parent.headers)
    assert error_code(off_topic) == "insufficient_context"

    fake_llm(_understood(), _explained(enough_information=False, explanation="", sources_used=[]))
    ungrounded = await client.post(f"{API}/learn/explain", json=payload, headers=parent.headers)
    assert error_code(ungrounded) == "insufficient_context"


async def test_parents_choose_the_child_and_child_mode_uses_itself(client: AsyncClient, fake_llm):
    parent, child, _ = await _family_with_book(client)

    fake_llm(_understood(), _explained())
    no_child = await client.post(
        f"{API}/learn/explain", json={"question": "Solve 2x"}, headers=parent.headers
    )
    assert no_child.status_code == 422

    fake = fake_llm(_understood(), _explained())
    session = await start_child_session(client, parent, child["id"])
    response = await client.post(
        f"{API}/learn/explain", json={"question": "Solve 2x + 4 = 10"}, headers=session
    )
    assert response.status_code == 200
    assert "Class 8" in fake.requests[1]["system"]


async def test_another_familys_book_or_chapter_is_never_used(client: AsyncClient, fake_llm):
    _, _, book = await _family_with_book(client)
    stranger = await register(client)
    their_child = await add_child(client, stranger, class_level="class_8")

    for scope in ({}, {"book_id": book["id"]}):
        fake_llm(_understood(), _explained())
        response = await client.post(
            f"{API}/learn/explain",
            json={"question": "Solve 2x + 4 = 10", "student_id": their_child["id"], **scope},
            headers=stranger.headers,
        )
        assert response.status_code in (404, 422)
        assert error_code(response) in ("book_not_found", "insufficient_context")
