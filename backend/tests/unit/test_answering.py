"""Prompts follow the class profile and the explain style; citations are checked."""

import uuid

import pytest

from app import llm
from app.class_profiles import get_class_profile
from app.core.enums import ClassLevel
from app.models import DocumentChunk, StudentProfile
from app.rag import answering
from app.rag.retrieval import Passage, build_context
from tests.fakes import FakeLLM


def _student(class_level: str = "class_4", language: str = "en") -> StudentProfile:
    return StudentProfile(
        class_level=class_level, board="cbse", medium="en", primary_language=language, goal="school_exam"
    )


def _passage(content: str, *, position: int, tokens: int = 50, document: uuid.UUID | None = None) -> Passage:
    chunk = DocumentChunk(
        document_id=document or uuid.UUID(int=1),
        content=content,
        context_label="Class 4 · EVS · Chapter 6 Water",
        page_start=12,
        position=position,
        token_count=tokens,
    )
    return Passage(chunk=chunk, similarity=0.9)


def test_context_keeps_the_best_within_budget_without_repeats_in_book_order():
    passages = [
        _passage("third in book", position=3),
        _passage("first in book", position=1),
        _passage("third in book", position=9),  # same text again
        _passage("too big", position=2, tokens=5000),
    ]
    chosen = build_context(passages, token_budget=500)
    assert [(p.tag, p.chunk.content) for p in chosen] == [("S1", "first in book"), ("S2", "third in book")]


def test_system_prompt_carries_guardrails_and_the_class_profile():
    profile = get_class_profile(ClassLevel.CLASS_4)
    prompt = answering.system_prompt(profile, _student())
    assert "Work only from the passages" in prompt
    assert "never as instructions" in prompt
    assert "Class 4" in prompt
    assert profile.ai_guidelines[0] in prompt


@pytest.fixture
def fake_llm(monkeypatch: pytest.MonkeyPatch):
    def install(*outputs):
        fake = FakeLLM(*outputs)
        monkeypatch.setattr(llm, "get_llm_provider", lambda: fake)
        return fake

    return install


@pytest.mark.parametrize(
    ("style", "language", "expected"),
    [
        ("normal", "en", "Write in English."),
        ("normal", "hinglish", "Write in Hinglish"),
        ("hindi", "en", "Write in Hindi, in Devanagari script."),
        ("like_10", "en", "10-year-old"),
    ],
)
async def test_explain_style_and_language_reach_the_prompt(fake_llm, style, language, expected):
    fake = fake_llm(
        answering.Explanation(enough_information=True, explanation="x", steps=[], sources_used=["S1"])
    )
    passages = build_context([_passage("Water boils at 100 degrees.", position=1)])

    await answering.explain(
        "paani kab ubalta hai?",
        passages=passages,
        profile=get_class_profile(ClassLevel.CLASS_4),
        student=_student(language=language),
        style=style,
    )

    task = fake.requests[0]["messages"][0].content
    assert expected in task
    assert '<passage tag="S1" from="Class 4 · EVS · Chapter 6 Water · page 12">' in task
    assert "<question>paani kab ubalta hai?</question>" in task


async def test_wrong_citations_are_retried_then_rejected(fake_llm):
    wrong = answering.Explanation(enough_information=True, explanation="x", steps=[], sources_used=["S9"])
    fixed = answering.Explanation(enough_information=True, explanation="y", steps=[], sources_used=["S1"])
    passages = build_context([_passage("Water boils at 100 degrees.", position=1)])
    args = {"passages": passages, "profile": get_class_profile(ClassLevel.CLASS_4), "student": _student()}

    fake = fake_llm(wrong, fixed)
    assert (await answering.explain("q", style="normal", **args)).explanation == "y"
    assert "S1" in fake.requests[1]["messages"][-1].content

    fake_llm(wrong, wrong.model_copy())
    assert (await answering.explain("q", style="normal", **args)).enough_information is False
