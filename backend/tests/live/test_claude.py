"""Real calls to Claude - catch prompt and schema problems the fakes cannot.

    pytest -m live      (needs ANTHROPIC_API_KEY in backend/.env; costs a fraction of a cent)

Not part of the normal `pytest` run.
"""

import anthropic
import pytest

from app.class_profiles import get_class_profile
from app.core.config import get_settings
from app.core.enums import ClassLevel
from app.llm import Message
from app.llm.anthropic_provider import AnthropicProvider
from app.models import DocumentChunk, StudentProfile
from app.rag.answering import Explanation, format_passages, system_prompt
from app.rag.retrieval import Passage, build_context

pytestmark = pytest.mark.live

API_KEY = get_settings().anthropic_api_key  # read from backend/.env, even though tests switch AI off


@pytest.fixture
def provider() -> AnthropicProvider:
    if not API_KEY:
        pytest.skip("ANTHROPIC_API_KEY is not set in backend/.env")
    model = "claude-opus-5-5"
    return AnthropicProvider(
        anthropic.AsyncAnthropic(api_key=API_KEY), {"fast": model, "default": model, "strong": model}
    )


async def test_grounded_explanation_in_hinglish(provider: AnthropicProvider):
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
