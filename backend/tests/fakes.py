"""Test doubles for external providers. They live only under tests/ (docs/01-architecture.md, rule 7)."""

import hashlib
import math
import re
from collections.abc import Sequence

from pydantic import BaseModel

from app.llm import LLMResult, RequestSize
from app.models.library import EMBEDDING_DIMENSION
from app.question_generation.schemas import GeneratedBatch, GeneratedQuestion, Review, ReviewBatch
from app.rag.ocr import OCRError, OCRPage


class FakeOCR:
    """Returns the same page text for every image, and records what it was asked."""

    def __init__(self, lines: list[str] | None = None, *, fail: bool = False) -> None:
        self.lines = lines or [
            "Chapter 6",
            "Our Environment",
            "6.1 Air and Water",
            "Air is all around us. We cannot see air but we can feel it when the wind blows.",
            "Plants and animals need clean air and water to live and grow.",
        ]
        self.fail = fail
        self.calls: list[tuple[int, tuple[str, ...]]] = []

    async def read_page(self, image_png: bytes, *, languages: Sequence[str]) -> OCRPage:
        self.calls.append((len(image_png), tuple(languages)))
        if self.fail:
            raise OCRError("simulated failure")
        return OCRPage(lines=list(self.lines))


class FakeEmbeddings:
    """Bag-of-words vectors: texts that share words (of 3+ letters) are close. Instant and offline."""

    model_name = "test-bag-of-words"
    min_similarity = 0.2

    def __init__(self) -> None:
        self.calls = 0

    @staticmethod
    def _vector(text: str) -> list[float]:
        vector = [0.0] * EMBEDDING_DIMENSION
        for word in re.findall(r"\w{3,}", text.casefold()):
            vector[int(hashlib.md5(word.encode()).hexdigest(), 16) % EMBEDDING_DIMENSION] += 1.0  # noqa: S324
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]

    async def embed_passages(self, texts: Sequence[str]) -> list[list[float]]:
        self.calls += 1
        return [self._vector(text) for text in texts]

    async def embed_query(self, text: str) -> list[float]:
        return self._vector(text)


class FakeLLM:
    """Answers each schema with the next scripted output, streams the next scripted reply word by
    word, and records every request. A reply can be a list of text and errors, raised where they
    stand (an error first = the stream fails at once)."""

    request_size = RequestSize()

    def __init__(self, *outputs: BaseModel, replies: Sequence[str | Exception | list] = ()) -> None:
        self.outputs = list(outputs)
        self.replies = list(replies)
        self.requests: list[dict] = []

    async def generate_structured(self, *, system, messages, schema, tier="default", max_output_tokens=16000):
        self.requests.append({"system": system, "messages": list(messages), "schema": schema, "tier": tier})
        output = next(item for item in self.outputs if isinstance(item, schema))
        self.outputs.remove(output)
        return LLMResult(output=output, model="fake", input_tokens=0, output_tokens=0, latency_ms=0.0)

    async def stream_text(self, *, system, messages, tier="default", max_output_tokens=16000):
        self.requests.append({"system": system, "messages": list(messages), "schema": None, "tier": tier})
        reply = self.replies.pop(0)
        for part in reply if isinstance(reply, list) else [reply]:
            if isinstance(part, Exception):
                raise part
            for piece in re.findall(r"\S+\s*", part):
                yield piece


def make_question(**overrides: object) -> GeneratedQuestion:
    """A valid Class 6-8 MCQ unless overridden."""
    values: dict = {
        "format": "mcq",
        "style": "recall",
        "difficulty": "medium",
        "case": None,
        "text": "What is x if 2x + 4 = 10?",
        "options": ["1", "2", "3", "4"],
        "correct_option": 2,
        "numeric_answer": None,
        "unit": None,
        "accepted_answers": [],
        "match_left": [],
        "match_right": [],
        "model_answer": None,
        "key_points": [],
        "hints": ["Take 4 away from both sides.", "Then divide both sides by 2."],
        "concept": "Do the same thing to both sides of an equation.",
        "steps": ["2x = 6", "x = 3"],
        "final_answer": "x = 3",
        "source_tags": ["S1"],
    }
    return GeneratedQuestion(**{**values, **overrides})


class QuestionWriterFake:
    """Writes the scripted batches of questions. Its reviewer agrees with every question, except
    the ones whose text is in `reject`. Other schemas are answered from `extra`."""

    _BLOCK = re.compile(r"Q(\d+) \[[^\]]+\]\n(.*?)(?=\n\nQ\d+ \[|\n</questions>)", re.S)

    def __init__(
        self,
        *batches: list[GeneratedQuestion],
        reject: Sequence[str] = (),
        extra: Sequence = (),
        request_size: RequestSize | None = None,
    ) -> None:
        self.request_size = request_size or RequestSize()
        self.batches = list(batches)
        self.reject = set(reject)
        self.extra = list(extra)
        self.known: dict[str, GeneratedQuestion] = {}
        self.requests: list[dict] = []

    def _review(self, number: int, question: GeneratedQuestion) -> Review:
        good = question.text not in self.reject
        return Review(
            number=number,
            solved_option=question.correct_option,
            solved_value=question.numeric_answer,
            solved_text=question.accepted_answers[0] if question.accepted_answers else None,
            shown_answer_correct=True,
            supported_by_passages=good,
            fits_class=True,
            difficulty=question.difficulty,
            problem="" if good else "not in the passages",
        )

    async def generate_structured(self, *, system, messages, schema, tier="default", max_output_tokens=16000):
        self.requests.append({"system": system, "messages": list(messages), "schema": schema, "tier": tier})
        if schema is GeneratedBatch:
            batch = self.batches.pop(0)
            self.known.update({question.text: question for question in batch})
            output: BaseModel = GeneratedBatch(questions=batch)
        elif schema is ReviewBatch:
            reviews = []
            for number, block in self._BLOCK.findall(messages[0].content):
                question = next(q for text, q in self.known.items() if text in block)
                reviews.append(self._review(int(number), question))
            output = ReviewBatch(reviews=reviews)
        else:
            output = next(item for item in self.extra if isinstance(item, schema))
            self.extra.remove(output)
        return LLMResult(output=output, model="fake", input_tokens=0, output_tokens=0, latency_ms=0.0)
