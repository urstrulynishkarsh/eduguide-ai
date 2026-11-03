"""Remove what repeats on every page: running headers, footers, page numbers, "Reprint 2025-26".

Without this, every chunk of an NCERT book would start with the book title and end with a page
number, which confuses both search and the AI.
"""

import re
import statistics
from collections import Counter

from app.rag.ingestion.text_quality import to_ascii_digits
from app.rag.ingestion.types import PageText

# How many lines at the top and bottom of a page can be a header or footer.
_EDGE_LINES = 3
# A line is "repeating" when it appears near the edge of at least this share of pages.
_REPEAT_SHARE = 0.4
_MIN_PAGES = 4

_PAGE_NUMBER = re.compile(
    # 12, - 12 -, Page 3 of 9
    r"^(?:(?:page|पृष्ठ)\s*)?[-–—\[]?\s*\d{1,4}\s*[-–—\]]?(?:\s*(?:of|/)\s*\d{1,4})?$"
    r"|^[ivxlc]{1,7}$",  # front-matter pages: iv, vii (bare only - "(i)" is an exercise part)
    re.IGNORECASE,
)
# A line this much larger than the body text is a real heading and is kept even if it repeats
# (a chapter title can also be the running header).
_HEADING_SIZE_RATIO = 1.25


def _shape(text: str) -> str:
    """Compare lines without their numbers: "Mathematics 45" and "Mathematics 46" are the same header."""
    return re.sub(r"\d+", "#", to_ascii_digits(text).casefold()).strip()


def _edge_indexes(page: PageText) -> set[int]:
    count = len(page.lines)
    return set(range(min(_EDGE_LINES, count))) | set(range(max(0, count - _EDGE_LINES), count))


def is_page_number(text: str) -> bool:
    return bool(_PAGE_NUMBER.match(to_ascii_digits(text).strip()))


def remove_page_furniture(pages: list[PageText]) -> None:
    """Remove repeating headers / footers and bare page numbers, in place."""
    numbered = [page for page in pages if page.number is not None]
    repeating: set[str] = set()
    if len(numbered) >= _MIN_PAGES:
        seen = Counter()
        for page in numbered:
            seen.update({_shape(page.lines[index].text) for index in _edge_indexes(page)})
        threshold = max(3, round(len(numbered) * _REPEAT_SHARE))
        repeating = {shape for shape, count in seen.items() if count >= threshold and shape}

    sizes = [line.size for page in numbered for line in page.lines if line.size]
    heading_size = statistics.median(sizes) * _HEADING_SIZE_RATIO if sizes else None

    for page in numbered:
        edges = _edge_indexes(page)
        kept = []
        for index, line in enumerate(page.lines):
            is_heading = heading_size is not None and line.size is not None and line.size >= heading_size
            if index in edges and (
                is_page_number(line.text) or (_shape(line.text) in repeating and not is_heading)
            ):
                continue
            kept.append(line)
        page.lines = kept
