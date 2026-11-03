"""Stage 4 - cut the book into labelled chunks (docs/05-rag-pipeline.md §5.3).

* A chunk never crosses a chapter or exercise boundary (segments already respect them).
* One exercise question = one chunk. One worked example = one chunk. Never split, never merged.
* Explanations are cut at line boundaries into pieces of about 300-500 tokens, preferring the end
  of a sentence, with a small overlap so a sentence cut in two is still found.
"""

import re
from dataclasses import dataclass, field, replace

from app.core.enums import ContentType
from app.rag.ingestion.structure import DocumentStructure, Line, Segment
from app.rag.ingestion.text_quality import estimate_tokens, letter_count

TARGET_TOKENS = 400
MIN_TOKENS = 300  # start looking for a sentence end from here
MAX_TOKENS = 500  # cut here even in the middle of a sentence
OVERLAP_TOKENS = 50
_SMALL_TAIL_TOKENS = 80  # a last piece smaller than this is joined to the one before
_SENTENCE_END = (".", "?", "!", "।", "॥", ":", ";")
_KEEP_WHOLE = {ContentType.EXERCISE_QUESTION, ContentType.EXAMPLE}
_SENTENCE_BREAK = re.compile(r"(?<=[.?!।॥])\s+")


@dataclass(slots=True)
class ChunkDraft:
    content_type: ContentType
    content: str
    chapter: int | None
    topic: int | None
    exercise: int | None
    page_start: int | None
    page_end: int | None
    token_count: int
    meta: dict[str, str] = field(default_factory=dict)


def join_lines(lines: list[Line]) -> str:
    """Join lines, repairing words broken with a hyphen at the end of a line ("equa-" + "tion")."""
    parts: list[str] = []
    for line in lines:
        text = line.text
        if parts and parts[-1].endswith("-") and not parts[-1].endswith(" -") and text[:1].islower():
            parts[-1] = parts[-1][:-1] + text
        else:
            parts.append(text)
    return "\n".join(parts)


def _pages(lines: list[Line]) -> tuple[int | None, int | None]:
    pages = [line.page for line in lines if line.page is not None]
    return (pages[0], pages[-1]) if pages else (None, None)


def _draft(segment: Segment, lines: list[Line]) -> ChunkDraft:
    content = join_lines(lines)
    page_start, page_end = _pages(lines)
    return ChunkDraft(
        content_type=segment.kind,
        content=content,
        chapter=segment.chapter,
        topic=segment.topic,
        exercise=segment.exercise,
        page_start=page_start,
        page_end=page_end,
        token_count=estimate_tokens(content),
        meta=dict(segment.meta),
    )


def _short_lines(lines: list[Line]) -> list[Line]:
    """Break lines longer than a chunk (a whole Word paragraph is one line) into sentences."""
    result: list[Line] = []
    for line in lines:
        if estimate_tokens(line.text) <= MAX_TOKENS:
            result.append(line)
            continue
        for sentence in _SENTENCE_BREAK.split(line.text):
            words = sentence.split()
            # A "sentence" without full stops (a long list, an OCR page) is cut by word count,
            # using this sentence's own tokens-per-word (Hindi words cost more tokens).
            tokens = estimate_tokens(sentence)
            step = max(1, len(words) if tokens <= MAX_TOKENS else len(words) * TARGET_TOKENS // tokens)
            for start in range(0, len(words), step):
                result.append(replace(line, text=" ".join(words[start : start + step])))
    return result


def _split(lines: list[Line]) -> list[list[Line]]:
    """Cut a long run of lines into pieces of MIN-MAX tokens with an overlap between them."""
    pieces: list[list[Line]] = []
    current: list[Line] = []
    tokens = 0
    for line in _short_lines(lines):
        line_tokens = estimate_tokens(line.text)
        if current and tokens + line_tokens > MAX_TOKENS:
            pieces.append(current)
            current = _overlap(current)
            tokens = sum(estimate_tokens(item.text) for item in current)
        current.append(line)
        tokens += line_tokens
        if tokens >= MIN_TOKENS and line.text.endswith(_SENTENCE_END):
            pieces.append(current)
            current = _overlap(current)
            tokens = sum(estimate_tokens(item.text) for item in current)

    overlap_only = len(pieces) > 0 and current == _overlap(pieces[-1])
    if current and not overlap_only:
        tail_tokens = sum(estimate_tokens(item.text) for item in current)
        previous_tokens = sum(estimate_tokens(item.text) for item in pieces[-1]) if pieces else 0
        if pieces and tail_tokens < _SMALL_TAIL_TOKENS and previous_tokens + tail_tokens <= MAX_TOKENS + 50:
            overlap = len(_overlap(pieces[-1]))
            pieces[-1] = pieces[-1] + current[overlap:]
        else:
            pieces.append(current)
    return pieces


def _overlap(piece: list[Line]) -> list[Line]:
    """The last lines of a piece, up to OVERLAP_TOKENS, to repeat at the start of the next one."""
    overlap: list[Line] = []
    tokens = 0
    for line in reversed(piece[1:]):  # never the whole piece
        tokens += estimate_tokens(line.text)
        if tokens > OVERLAP_TOKENS:
            break
        overlap.insert(0, line)
    return overlap


def make_chunks(structure: DocumentStructure) -> list[ChunkDraft]:
    """Chunks in reading order."""
    drafts: list[ChunkDraft] = []
    for segment in structure.segments:
        text = " ".join(line.text for line in segment.lines)
        if letter_count(text) + sum(ch.isdigit() for ch in text) < 3:
            continue  # nothing worth searching for
        if segment.kind in _KEEP_WHOLE or estimate_tokens(join_lines(segment.lines)) <= MAX_TOKENS:
            drafts.append(_draft(segment, segment.lines))
            continue
        drafts.extend(_draft(segment, piece) for piece in _split(segment.lines))
    return drafts
