"""Test doubles for external providers. They live only under tests/ (docs/01-architecture.md, rule 7)."""

import hashlib
import math
import re
from collections.abc import Sequence

from pydantic import BaseModel

from app.llm import LLMResult
from app.models.library import EMBEDDING_DIMENSION
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
    """Answers each schema with the next scripted output, and records every request."""

    def __init__(self, *outputs: BaseModel) -> None:
        self.outputs = list(outputs)
        self.requests: list[dict] = []

    async def generate_structured(self, *, system, messages, schema, tier="default", max_output_tokens=16000):
        self.requests.append({"system": system, "messages": list(messages), "schema": schema, "tier": tier})
        output = next(item for item in self.outputs if isinstance(item, schema))
        self.outputs.remove(output)
        return LLMResult(output=output, model="fake", input_tokens=0, output_tokens=0, latency_ms=0.0)
