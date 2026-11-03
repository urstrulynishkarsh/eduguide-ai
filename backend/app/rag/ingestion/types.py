"""Plain data passed between the reading stages."""

from dataclasses import dataclass, field
from typing import Literal

PageSource = Literal["text", "ocr", "none"]


@dataclass(slots=True)
class TextLine:
    text: str
    size: float | None = None  # font size, when the file format has one (PDF)
    bold: bool = False
    heading_level: int | None = None  # from DOCX heading styles: 0 = Title, 1 = Heading 1...


@dataclass(slots=True)
class PageText:
    """One page. `number` is the 1-based page number, or None when the format has no pages."""

    number: int | None
    lines: list[TextLine] = field(default_factory=list)
    source: PageSource = "text"


@dataclass(slots=True)
class OutlineEntry:
    """One PDF bookmark."""

    title: str
    level: int
    page: int | None  # 1-based


@dataclass(slots=True)
class ExtractedDocument:
    pages: list[PageText]
    outline: list[OutlineEntry] = field(default_factory=list)
    page_count: int | None = None
    ocr_pages: int = 0
    unreadable_pages: int = 0  # needed OCR but could not get it
