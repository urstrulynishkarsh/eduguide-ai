"""Test doubles for external providers. They live only under tests/ (docs/01-architecture.md, rule 7)."""

from collections.abc import Sequence

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
