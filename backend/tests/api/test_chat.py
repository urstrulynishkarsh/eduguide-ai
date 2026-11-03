"""The Parent AI Assistant and the Student AI Tutor: streamed replies, sources, the hint ladder, who sees
what. The AI is scripted (tests/fakes.py); replies stream word by word."""

import json
import re
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import llm
from app.chat.assistant import Understanding as AssistantUnderstanding
from app.chat.tutor import Understanding as TutorUnderstanding
from app.models import ChatMessage
from tests.api.helpers import API, add_child, error_code, family_with_book, register, start_child_session
from tests.fakes import FakeLLM


@pytest.fixture
def ai(monkeypatch: pytest.MonkeyPatch):
    def install(fake: FakeLLM) -> FakeLLM:
        monkeypatch.setattr(llm, "get_llm_provider", lambda: fake)
        return fake

    return install


def _events(body: str) -> list[tuple[str, dict]]:
    events = []
    for block in body.strip().split("\n\n"):
        fields = dict(line.split(": ", 1) for line in block.split("\n"))
        events.append((fields["event"], json.loads(fields["data"])))
    return events


async def _chat(client: AsyncClient, headers: dict, kind: str, student_id: str | None = None) -> dict:
    body = {"kind": kind, **({"student_id": student_id} if student_id else {})}
    response = await client.post(f"{API}/chat/sessions", json=body, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


async def _say(client: AsyncClient, headers: dict, chat: dict, text: str):
    return await client.post(
        f"{API}/chat/sessions/{chat['id']}/messages", json={"text": text}, headers=headers
    )


def _tutor(intent: str, query: str = "", hints_only: bool = False) -> TutorUnderstanding:
    return TutorUnderstanding(intent=intent, hints_only=hints_only, search_query=query)


async def test_the_parent_assistant_answers_from_the_app_and_the_books(client: AsyncClient, ai):
    parent, child, _ = await family_with_book(client)
    fake = ai(
        FakeLLM(
            AssistantUnderstanding(on_topic=True, needs_books=True, search_query="solve equation both sides"),
            replies=[
                "Aarav is just starting this chapter. It teaches doing the same thing on both sides [S1]."
            ],
        )
    )
    chat = await _chat(client, parent.headers, "assistant", child["id"])

    response = await _say(client, parent.headers, chat, "How can I help Aarav with equations?")

    assert response.status_code == 200 and response.headers["content-type"].startswith("text/event-stream")
    events = _events(response.text)
    deltas = [data["text"] for name, data in events if name == "delta"]
    assert len(deltas) > 3 and "".join(deltas).endswith("[S1].")
    name, done = events[-1]
    assert name == "done" and done["question"]["content"] == "How can I help Aarav with equations?"
    answer = done["answer"]
    assert answer["content"].endswith("both sides.")  # the passage tag is replaced by the sources
    assert answer["rung"] is None

    # The model got the app's own numbers and the passage, but not the child's name.
    reply_request = fake.requests[-1]
    task = reply_request["messages"][-1].content
    (source,) = answer["sources"]
    assert source["chapter"] in re.search(r'<passage tag="S1" from="([^"]+)"', task).group(1)
    assert "<child_data>" in task and '"questions_answered": 0' in task and '<passage tag="S1"' in task
    assert child["name"] not in reply_request["system"] + task.split("<question>")[0]
    assert "Class 7" in reply_request["system"]

    saved = (await client.get(f"{API}/chat/sessions/{chat['id']}", headers=parent.headers)).json()
    assert saved["title"] == "How can I help Aarav with equations?"
    assert [(m["role"], m["content"]) for m in saved["messages"]] == [
        ("user", "How can I help Aarav with equations?"),
        ("assistant", answer["content"]),
    ]
    listed = await client.get(
        f"{API}/chat/sessions",
        params={"kind": "assistant", "student_id": child["id"]},
        headers=parent.headers,
    )
    assert [item["id"] for item in listed.json()["items"]] == [chat["id"]]


async def test_the_tutor_climbs_the_hint_ladder_one_rung_at_a_time(client: AsyncClient, ai):
    parent, child, _ = await family_with_book(client)
    learner = await start_child_session(client, parent, child["id"])
    chat = await _chat(client, learner, "tutor")
    fake = ai(
        FakeLLM(
            _tutor("new_problem", "solve equation both sides"),
            _tutor("show_answer"),
            _tutor("attempt"),
            replies=[
                "What could you take away from both sides? [S1]",
                "Use the rule: same on both sides.",
                "Close!",
            ],
        )
    )

    rungs = []
    for text in ("Solve 2x + 4 = 10", "Just tell me the answer!", "x = 7"):
        response = await _say(client, learner, chat, text)
        assert response.status_code == 200, response.text
        rungs.append(_events(response.text)[-1][1]["answer"]["rung"])

    assert rungs == ["hint_1", "hint_2", "concept"]  # "the answer" only moved one rung
    replies = [r["messages"] for r in fake.requests if r["schema"] is None]
    assert replies[1][-1].content.startswith("This reply is Hint 2")
    assert "<problem>Solve 2x + 4 = 10</problem>" in replies[1][-1].content
    assert replies[2][-1].content.startswith("The student has tried an answer")
    # The conversation so far goes along with each reply request.
    assert [m.content for m in replies[2][:-1]][-2:] == [
        "<message>Just tell me the answer!</message>",
        "Use the rule: same on both sides.",
    ]
    assert "Do not" not in fake.requests[0]["system"]  # the understanding call has its own short rules
    # The parent can read the child's tutor; the learner cannot read the parent's assistant.
    assert (await client.get(f"{API}/chat/sessions/{chat['id']}", headers=parent.headers)).status_code == 200


async def test_nothing_is_saved_when_the_reply_fails_or_the_books_do_not_cover_it(
    client: AsyncClient, ai, db_session: AsyncSession
):
    parent, child, _ = await family_with_book(client)
    learner = await start_child_session(client, parent, child["id"])
    chat = await _chat(client, learner, "tutor")

    off = await _say(client, learner, chat, "Solve 2x + 4 = 10")
    assert (off.status_code, error_code(off)) == (503, "ai_not_configured")

    ai(FakeLLM(_tutor("new_problem", "photosynthesis chlorophyll leaves")))
    uncovered = await _say(client, learner, chat, "What is photosynthesis?")
    assert (uncovered.status_code, error_code(uncovered)) == (422, "insufficient_context")

    ai(
        FakeLLM(
            _tutor("new_problem", "solve equation both sides"),
            replies=[["Take away", llm.AIUnavailableError()]],
        )
    )
    broken = _events((await _say(client, learner, chat, "Solve 2x + 4 = 10")).text)
    assert [name for name, _ in broken] == ["delta", "delta", "error"]
    assert broken[-1][1]["code"] == "ai_unavailable"

    count = await db_session.scalar(
        select(func.count()).where(ChatMessage.session_id == uuid.UUID(chat["id"]))
    )
    assert count == 0


async def test_only_the_family_sees_its_conversations(client: AsyncClient, ai):
    parent, child, _ = await family_with_book(client)
    sibling = await add_child(client, parent, class_level="class_7")
    learner = await start_child_session(client, parent, child["id"])
    stranger = await register(client)
    assistant_chat = await _chat(client, parent.headers, "assistant", child["id"])
    tutor_chat = await _chat(client, learner, "tutor")

    refused = await client.post(f"{API}/chat/sessions", json={"kind": "assistant"}, headers=learner)
    assert (refused.status_code, error_code(refused)) == (403, "parent_required")
    for headers, chat in (
        (learner, assistant_chat),
        (stranger.headers, tutor_chat),
        (stranger.headers, assistant_chat),
    ):
        for method in ("GET", "DELETE"):
            response = await client.request(method, f"{API}/chat/sessions/{chat['id']}", headers=headers)
            assert (response.status_code, error_code(response)) == (404, "chat_not_found")
        sent = await _say(client, headers, chat, "Hello")
        assert sent.status_code == 404
    elsewhere = await client.post(
        f"{API}/chat/sessions",
        json={"kind": "assistant", "student_id": child["id"]},
        headers=stranger.headers,
    )
    assert error_code(elsewhere) == "student_not_found"
    sibling_list = await client.get(
        f"{API}/chat/sessions", params={"kind": "tutor", "student_id": sibling["id"]}, headers=parent.headers
    )
    assert sibling_list.json()["items"] == []
    mine = await client.get(f"{API}/chat/sessions", params={"kind": "tutor"}, headers=learner)
    assert [item["id"] for item in mine.json()["items"]] == [tutor_chat["id"]]

    assert (
        await client.delete(f"{API}/chat/sessions/{tutor_chat['id']}", headers=learner)
    ).status_code == 204
    assert (await client.get(f"{API}/chat/sessions/{tutor_chat['id']}", headers=learner)).status_code == 404
