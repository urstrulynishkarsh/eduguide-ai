"""Write -> check -> review -> replace: the generation loop with a scripted AI."""

import uuid

import pytest

from app import llm
from app.class_profiles import get_class_profile
from app.core.enums import ClassLevel, QuestionFormat
from app.models import DocumentChunk, StudentProfile
from app.question_generation import generator
from app.rag.retrieval import Passage, build_context
from tests.fakes import QuestionWriterFake, make_question

CLASS_8 = get_class_profile(ClassLevel.CLASS_8)
CLASS_12 = get_class_profile(ClassLevel.CLASS_12)


def _passages() -> list[Passage]:
    chunk = DocumentChunk(
        document_id=uuid.UUID(int=1),
        content="Example 2: Solve 2x + 4 = 10. Subtract 4 from both sides: 2x = 6, so x = 3.",
        context_label="Class 8 · Mathematics · Chapter 2 Linear Equations · Example 2",
        page_start=3,
        position=0,
        token_count=30,
    )
    return build_context([Passage(chunk, 1.0)])


def _student(class_level="class_8", goal="school_exam") -> StudentProfile:
    return StudentProfile(
        class_level=class_level, board="cbse", medium="en", primary_language="en", goal=goal
    )


def _request(count=3, formats=(QuestionFormat.MCQ, QuestionFormat.SHORT_ANSWER), language="en"):
    return generator.Request(count=count, difficulty="mixed", formats=list(formats), language=language)


@pytest.fixture
def writer(monkeypatch: pytest.MonkeyPatch):
    def install(*batches, reject=()) -> QuestionWriterFake:
        fake = QuestionWriterFake(*batches, reject=reject)
        monkeypatch.setattr(llm, "get_llm_provider", lambda: fake)
        return fake

    return install


async def test_good_questions_are_kept_and_failures_replaced(writer):
    good = [make_question(text=f"Question {n}: what is x if 2x + {n} = 10?") for n in range(2)]
    broken = make_question(text="Broken: which option?", options=["1", "2"])  # wrong option count
    rejected = make_question(text="Rejected: what is the colour of x?")  # the reviewer says no
    replacement = make_question(text="Replacement: solve 3x = 9.")
    fake = writer([*good, broken], [rejected], [replacement], reject=[rejected.text])

    kept = await generator.generate(
        _passages(), profile=CLASS_8, student=_student(), request=_request(count=3), existing=[]
    )

    assert [q.text for q in kept] == [good[0].text, good[1].text, replacement.text]
    writes = [r for r in fake.requests if r["schema"].__name__ == "GeneratedBatch"]
    reviews = [r for r in fake.requests if r["schema"].__name__ == "ReviewBatch"]
    assert len(writes) == 3
    assert all(r["tier"] == "strong" for r in reviews)
    second_task = writes[1]["messages"][0].content
    assert "Write 1 questions." in second_task
    assert "exactly 4 different, non-empty options" in second_task  # the reason went back to the writer
    assert "not everything needed is in the passages" in writes[2]["messages"][0].content
    # The reviewer never sees the proposed answer of a choice question.
    assert "x = 3" not in reviews[0]["messages"][0].content.split("<questions>")[1]


async def test_after_the_last_round_fewer_questions_are_returned(writer):
    always_broken = [make_question(text=f"Broken {n}", options=["1"]) for n in range(3)]
    writer([always_broken[0]], [always_broken[1]], [always_broken[2]])

    kept = await generator.generate(
        _passages(), profile=CLASS_8, student=_student(), request=_request(count=1), existing=[]
    )
    assert kept == []


async def test_the_prompt_carries_class_goal_language_and_existing_questions(writer):
    fake = writer(
        [make_question(text="Find the momentum of a 2 kg ball moving at 3 m/s.", style="competitive_exam")]
    )

    await generator.generate(
        _passages(),
        profile=CLASS_12,
        student=_student("class_12", goal="jee"),
        request=_request(count=1, formats=[QuestionFormat.MCQ], language="hi"),
        existing=["What is velocity?"],
    )

    write = fake.requests[0]
    task = write["messages"][0].content
    assert "Class 12" in write["system"]
    assert "exactly 4 options" in write["system"]
    assert "joining two concepts" in task  # the JEE strategy
    assert "Write every question, hint and solution in Hindi." in task
    assert "what is velocity" in task  # existing questions are not repeated
    assert '<passage tag="S1"' in task
