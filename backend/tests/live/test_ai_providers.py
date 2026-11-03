"""Real calls to the AI providers - catch prompt and schema problems the fakes cannot.

    pytest -m live      (runs for each provider whose key is in backend/.env: ANTHROPIC_API_KEY
                         costs a fraction of a cent; GROQ_API_KEY uses the free plan's allowance)

Not part of the normal `pytest` run.
"""

import anthropic
import groq
import pytest

from app.class_profiles import get_class_profile
from app.core.config import get_settings
from app.core.enums import ClassLevel
from app.llm import LLMProvider, Message, anthropic_provider, groq_provider
from app.models import DocumentChunk, StudentProfile
from app.rag.answering import Explanation, format_passages, system_prompt
from app.rag.retrieval import Passage, build_context

pytestmark = pytest.mark.live

_settings = get_settings()  # keys are read from backend/.env, even though tests switch AI off


@pytest.fixture(params=["anthropic", "groq"])
def provider(request: pytest.FixtureRequest) -> LLMProvider:
    if request.param == "anthropic":
        if not _settings.anthropic_api_key:
            pytest.skip("ANTHROPIC_API_KEY is not set in backend/.env")
        client = anthropic.AsyncAnthropic(api_key=_settings.anthropic_api_key)
        return anthropic_provider.AnthropicProvider(client, anthropic_provider.DEFAULT_MODELS)
    if not _settings.groq_api_key:
        pytest.skip("GROQ_API_KEY is not set in backend/.env")
    client = groq.AsyncGroq(api_key=_settings.groq_api_key)
    return groq_provider.GroqProvider(client, groq_provider.DEFAULT_MODELS)


async def test_grounded_explanation_in_hinglish(provider: LLMProvider):
    chunk = DocumentChunk(
        content="Example 2: Solve 2x + 4 = 10.\nSolution: Subtract 4 from both sides, 2x = 6, so x = 3.",
        context_label="Class 7 · Mathematics · Chapter 4 Simple Equations · Example 2",
        page_start=None,
        position=0,
        token_count=40,
        document_id=None,
    )
    passages = build_context([Passage(chunk, 0.9)])
    student = StudentProfile(
        class_level="class_7", board="cbse", medium="en", primary_language="hinglish", goal="school_exam"
    )

    result = await provider.generate_structured(
        system=system_prompt(get_class_profile(ClassLevel.CLASS_7), student),
        messages=[
            Message(
                "user",
                "Explain the student's question using only the passages. Write in Hinglish.\n\n"
                f"{format_passages(passages)}\n\n<question>2x + 4 = 10 kaise solve karte hain?</question>",
            )
        ],
        schema=Explanation,
    )

    answer = result.output
    assert answer.enough_information
    assert answer.sources_used == ["S1"]
    assert "3" in answer.explanation
    assert result.input_tokens > 0


async def test_questions_are_written_and_pass_the_independent_review(
    provider: LLMProvider, monkeypatch: pytest.MonkeyPatch
):
    """The whole generation loop on a real model: schema accepted, checks passed, answers agreed."""
    from app import llm
    from app.core.enums import QuestionFormat
    from app.question_generation import generator

    monkeypatch.setattr(llm, "get_llm_provider", lambda: provider)
    chunk = DocumentChunk(
        content="To solve an equation we do the same operation on both sides. Example: 2x + 4 = 10. "
        "Subtract 4 from both sides to get 2x = 6. Divide both sides by 2, so x = 3.",
        context_label="Class 7 · Mathematics · Chapter 4 Simple Equations · 4.2 Solving an Equation",
        page_start=None,
        position=0,
        token_count=60,
        document_id=None,
    )
    student = StudentProfile(
        class_level="class_7", board="cbse", medium="en", primary_language="en", goal="school_exam"
    )

    questions = await generator.generate(
        build_context([Passage(chunk, 1.0)]),
        profile=get_class_profile(ClassLevel.CLASS_7),
        student=student,
        request=generator.Request(count=2, difficulty="easy", formats=[QuestionFormat.MCQ], language="en"),
        existing=[],
    )

    assert questions
    assert all(q.format is QuestionFormat.MCQ and q.source_tags == ["S1"] for q in questions)


async def test_a_tutor_hint_streams_without_giving_the_answer(provider: LLMProvider):
    """Streaming on a real model, with the tutor's first rung: a nudge, not the solution."""
    from app.chat import tutor

    chunk = DocumentChunk(
        content="To solve an equation we do the same operation on both sides.",
        context_label="Class 7 · Mathematics · Chapter 4 Simple Equations",
        page_start=None,
        position=0,
        token_count=20,
        document_id=None,
    )
    student = StudentProfile(
        class_level="class_7", board="cbse", medium="en", primary_language="en", goal="school_exam"
    )
    understood = tutor.Understanding(intent="new_problem", hints_only=False, search_query="")
    step = tutor.next_step(tutor.State(), understood, "Solve 2x + 4 = 10")

    pieces = [
        piece
        async for piece in provider.stream_text(
            system=tutor.system_prompt(get_class_profile(ClassLevel.CLASS_7), student),
            messages=[
                Message(
                    "user", tutor.task(step, "Solve 2x + 4 = 10", build_context([Passage(chunk, 1.0)]), "en")
                )
            ],
        )
    ]

    reply = "".join(pieces)
    assert len(pieces) > 1 and reply.strip()
    assert "x=3" not in reply.replace(" ", "")  # the answer waits for the last rung
