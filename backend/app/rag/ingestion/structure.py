"""Stage 3 - find the structure of a book (spec §14, docs/05-rag-pipeline.md §5.2).

    Book -> Chapter -> Topic / Example / Exercise -> Question
                    -> Summary

Evidence, cheapest first:
1. the PDF's own outline (bookmarks), when it lists at least two chapters;
2. headings found by pattern ("Chapter 4", "EXERCISE 2.3", "Example 5", "2.3 Solving Equations",
   "अध्याय", "प्रश्नावली", "उदाहरण") and by layout (larger or bold lines, Word heading styles);
3. otherwise the whole file is one chapter (NCERT publishes one PDF per chapter), numbered from
   the file name when possible.

(The AI-assisted fallback for unclear books is added once the AI layer exists, in Step 3.)

Everything here is pure: lines in, structure out. `StructureDetector` runs in three steps so the
progress checklist can show them: chapters -> exercises and questions -> topics.
"""

import re
import statistics
from dataclasses import dataclass, field
from pathlib import PurePath
from typing import Literal

from app.core.enums import ContentType
from app.rag.ingestion.text_quality import letter_count, to_ascii_digits
from app.rag.ingestion.types import OutlineEntry, PageText

# ------------------------------------------------------------------ patterns

_CHAPTER = re.compile(
    r"^(?P<word>chapter|chap\.|ch\.|unit|lesson|अध्याय|पाठ|इकाई)\s*[-:.]?\s*"
    r"(?P<num>\d{1,3}|[ivxlc]{1,7})(?![\w.])\s*[-:.–—]?\s*(?P<rest>.*)$",
    re.IGNORECASE,
)
_EXERCISE = re.compile(
    r"^(?P<word>exercises?|ex\.|प्रश्नावली|अभ्यास(?:\s*प्रश्न)?|(?:in-?\s?text\s+)?questions)"
    r"\s*[-:.]?\s*(?P<num>\d{1,2}(?:\.\d{1,2}){0,2})?\s*[:.]?\s*(?P<rest>\(.*\))?$",
    re.IGNORECASE,
)
_EXAMPLE = re.compile(
    r"^(?P<word>example|illustration|उदाहरण)\s*[-:.]?\s*(?P<num>\d{1,3}(?:\.\d{1,3})?)"
    r"(?![\d])\s*[-:.)–—]?\s*(?P<rest>.*)$",
    re.IGNORECASE,
)
_SUMMARY = re.compile(
    r"^(?:summary|summaries|what have we discussed|what we have discussed|points to remember|"
    r"key points|key concepts|let us recall|recap|सारांश|हमने क्या चर्चा की|याद रखने योग्य बातें|"
    r"स्मरणीय बिंदु)\s*[?:]?$",
    re.IGNORECASE,
)
_MATTER = re.compile(
    r"^(?:contents|table of contents|foreword|preface|acknowledge?ments?|index|glossary|"
    r"appendix(?:\s+[a-z0-9]{1,4})?|answers?|answer key|answers to exercises|bibliography|references|"
    r"विषय[- ]?सूची|अनुक्रमणिका|आमुख|प्राक्कथन|उत्तरमाला)\s*:?$",
    re.IGNORECASE,
)
_ANSWERS = re.compile(r"^(?:answers?|answer key|answers to exercises|उत्तरमाला)\s*:?$", re.IGNORECASE)
_CONTENTS = re.compile(r"^(?:contents|table of contents|विषय[- ]?सूची|अनुक्रमणिका)$", re.IGNORECASE)
_TOC_ENTRY = re.compile(r"(?:\.\s?){3,}\s*\d{1,3}$|…+\s*\d{1,3}$")
_NUMBERED_TOPIC = re.compile(r"^(?P<num>\d{1,2}\.\d{1,2}(?:\.\d{1,2})?)\.?\s+(?P<title>\S.*)$")
# "4. Solve..." or "4) Solve...". The space after the dot matters: "2.5 kg of rice" is not question 2.
_QUESTION = re.compile(r"^(?P<num>\d{1,3})\s*[.)](?:\s+(?P<rest>\S.*))?$")
_QUESTION_PREFIXED = re.compile(
    r"^(?:q|que|ques|question|प्रश्न)\.?\s*(?P<num>\d{1,3})\s*[.):]?\s*(?P<rest>.*)$", re.IGNORECASE
)
_SOLUTION = re.compile(r"^(?:solution|sol\.|answer|ans\.|हल)\b", re.IGNORECASE)
_LEADING_NUMBER = re.compile(r"^(?P<num>\d{1,2})\s*[.:)\-–]?\s+(?P<title>\S.*)$")
_NOT_A_TOPIC = re.compile(
    r"^(?:activity|solution|sol\.|answer|ans\.|hint|note|remember|try these|do this|think|figure|fig\.|"
    r"table|example|illustration|exercise|q\.|question|गतिविधि|क्रियाकलाप|हल|उत्तर|चित्र|सारणी)\b",
    re.IGNORECASE,
)
_ROMAN = re.compile(r"^M{0,3}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$")
_ROMAN_VALUES = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
_NCERT_FILE = re.compile(r"^[a-z]{4}\d(?P<num>\d{2})$", re.IGNORECASE)  # e.g. hemh102 = chapter 2
_FILE_CHAPTER = re.compile(
    r"(?:chapter|chap|ch|lesson|unit|adhyay|path)[\s_\-.]*(?P<num>\d{1,2})", re.IGNORECASE
)

_PROMINENT_RATIO = 1.1
_STRONG_RATIO = 1.2
_MAX_TITLE_WORDS = 14
_EXAMPLE_TAIL_TOKENS = 450  # concept text that follows a finished example is cut off after this
_MODE_CONTENT_TYPE = {
    "concept": ContentType.CONCEPT,
    "summary": ContentType.SUMMARY,
    "other": ContentType.OTHER,
}
_MAX_SHARED_INSTRUCTION_WORDS = 40  # "Solve the following equations." is repeated on every question


def roman_to_int(text: str) -> int | None:
    upper = text.upper()
    if not upper or not _ROMAN.match(upper):
        return None
    total, previous = 0, 0
    for char in reversed(upper):
        value = _ROMAN_VALUES[char]
        total = total - value if value < previous else total + value
        previous = max(previous, value)
    return total


def _parse_number(text: str) -> int | None:
    if text.isdigit():
        return int(text)
    if text.isupper():  # roman chapter numbers are written in capitals: "Chapter IV"
        value = roman_to_int(text)
        return value if value and value <= 60 else None
    return None


def chapter_number_from_filename(filename: str) -> int | None:
    stem = PurePath(filename).stem
    for pattern in (_NCERT_FILE, _FILE_CHAPTER):
        match = pattern.search(stem)
        if match:
            number = int(match.group("num"))
            return number if number > 0 else None
    return None


def _title_from_filename(filename: str) -> str:
    stem = PurePath(filename).stem
    words = re.sub(r"[_\-.]+", " ", stem).split()
    return " ".join(words)[:200] or "Chapter"


def _looks_like_prose(rest: str) -> bool:
    """'we learnt about fractions.' is a sentence, not a heading."""
    words = rest.split()
    if len(words) > _MAX_TITLE_WORDS:
        return True
    if words and words[0][0].islower():
        return True
    return rest.endswith((".", ",", ";")) and len(words) > 4


# ------------------------------------------------------------------ data


@dataclass(slots=True)
class Line:
    index: int
    page: int | None
    text: str
    size: float | None
    bold: bool
    heading_level: int | None
    on_contents_page: bool = False

    @property
    def ascii(self) -> str:
        return to_ascii_digits(self.text)


@dataclass(slots=True)
class DetectedTopic:
    number: str | None
    title: str
    page_start: int | None


@dataclass(slots=True)
class DetectedExercise:
    label: str
    page_start: int | None
    page_end: int | None = None
    question_count: int = 0


@dataclass(slots=True)
class DetectedChapter:
    number: int | None
    title: str
    detected_by: Literal["outline", "heading", "file"]
    page_start: int | None = None
    page_end: int | None = None
    topics: list[DetectedTopic] = field(default_factory=list)
    exercises: list[DetectedExercise] = field(default_factory=list)


@dataclass(slots=True)
class Segment:
    """A run of lines with one meaning. Chunking turns each segment into one or more chunks."""

    kind: ContentType
    chapter: int | None  # index into DocumentStructure.chapters
    topic: int | None  # index into that chapter's topics
    exercise: int | None  # index into that chapter's exercises
    lines: list[Line] = field(default_factory=list)
    meta: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class DocumentStructure:
    chapters: list[DetectedChapter]
    segments: list[Segment]

    @property
    def exercise_count(self) -> int:
        return sum(len(chapter.exercises) for chapter in self.chapters)

    @property
    def question_count(self) -> int:
        return sum(exercise.question_count for chapter in self.chapters for exercise in chapter.exercises)

    @property
    def topic_count(self) -> int:
        return sum(len(chapter.topics) for chapter in self.chapters)

    @property
    def example_count(self) -> int:
        return sum(1 for segment in self.segments if segment.kind is ContentType.EXAMPLE)


@dataclass(slots=True)
class _Span:
    """Where a chapter (or front / back matter, chapter=None) starts in the line list."""

    start: int
    chapter: DetectedChapter | None
    heading_lines: set[int] = field(default_factory=set)


@dataclass(slots=True)
class _Marker:
    kind: Literal["exercise", "example", "summary", "answers"]
    number: str | None = None


# ------------------------------------------------------------------ detector


class StructureDetector:
    def __init__(self, pages: list[PageText], *, outline: list[OutlineEntry], filename: str) -> None:
        self.filename = filename
        self.outline = outline
        self.lines: list[Line] = []
        for page in pages:
            for line in page.lines:
                self.lines.append(
                    Line(
                        index=len(self.lines),
                        page=page.number,
                        text=line.text,
                        size=line.size,
                        bold=line.bold,
                        heading_level=line.heading_level,
                    )
                )
        sizes = [line.size for line in self.lines if line.size]
        self.body_size = statistics.median(sizes) if sizes else None
        self.has_layout = self.body_size is not None or any(
            line.heading_level is not None for line in self.lines
        )
        self._mark_contents_pages()
        self.spans: list[_Span] = []
        self.markers: dict[int, _Marker] = {}

    # ---- layout helpers

    def _is_prominent(self, line: Line) -> bool:
        if line.heading_level is not None:
            return True
        if (
            self.body_size is not None
            and line.size is not None
            and line.size >= self.body_size * _PROMINENT_RATIO
        ):
            return True
        if line.bold:
            return True
        if not self.has_layout:
            # Plain text: short lines in capitals are the only sign of a heading.
            words = line.text.split()
            return 0 < len(words) <= 8 and line.text.isupper() and letter_count(line.text) >= 3
        return False

    def _is_strong(self, line: Line) -> bool:
        if line.heading_level is not None:
            return True
        if self.body_size is not None and line.size is not None:
            return line.size >= self.body_size * _STRONG_RATIO
        return not self.has_layout and self._is_prominent(line)

    def _mark_contents_pages(self) -> None:
        by_page: dict[int, list[Line]] = {}
        for line in self.lines:
            if line.page is not None:
                by_page.setdefault(line.page, []).append(line)
        for page_lines in by_page.values():
            heading = any(_CONTENTS.match(line.text) for line in page_lines[:6])
            entries = sum(1 for line in page_lines if _TOC_ENTRY.search(line.text))
            chapters = sum(1 for line in page_lines if _CHAPTER.match(line.ascii))
            if heading or entries >= 4 or chapters >= 3:
                for line in page_lines:
                    line.on_contents_page = True

    # ---- step 1: chapters

    def detect_chapters(self) -> list[DetectedChapter]:
        spans = self._spans_from_outline() or self._spans_from_headings() or self._spans_from_heading_styles()
        if not spans:
            spans = [self._whole_file_span()]
        self.spans = spans
        self._set_chapter_pages()
        return self.chapters

    @property
    def chapters(self) -> list[DetectedChapter]:
        return [span.chapter for span in self.spans if span.chapter is not None]

    def _parse_chapter_title(self, text: str) -> tuple[int | None, str]:
        match = _CHAPTER.match(to_ascii_digits(text))
        if match:
            number = _parse_number(match.group("num"))
            if number is not None:
                return number, match.group("rest").strip(" -:.–—") or f"Chapter {number}"
        leading = _LEADING_NUMBER.match(to_ascii_digits(text))
        if leading:
            return int(leading.group("num")), leading.group("title").strip()
        return None, text

    def _spans_from_outline(self) -> list[_Span]:
        entries = [entry for entry in self.outline if entry.page is not None]
        if not entries or not self.lines:
            return []
        # Use the shallowest outline level that lists at least two entries.
        levels = sorted({entry.level for entry in entries})
        chosen = next((lvl for lvl in levels if sum(1 for e in entries if e.level == lvl) >= 2), None)
        if chosen is None:
            return []
        level_entries = [entry for entry in entries if entry.level == chosen]
        if sum(1 for entry in level_entries if not _MATTER.match(entry.title)) < 2:
            return []

        spans: list[_Span] = []
        used: set[int] = set()
        for entry in level_entries:
            start = self._line_for_outline_entry(entry)
            if start is None or start in used:
                continue
            used.add(start)
            if _MATTER.match(entry.title):
                spans.append(_Span(start=start, chapter=None))
                continue
            number, title = self._parse_chapter_title(entry.title)
            heading = self._chapter_heading_at(self.lines[start])
            used = heading[2] if heading else {start}
            spans.append(
                _Span(
                    start=start, chapter=DetectedChapter(number, title[:300], "outline"), heading_lines=used
                )
            )
        spans.sort(key=lambda span: span.start)
        return spans if any(span.chapter for span in spans) else []

    def _line_for_outline_entry(self, entry: OutlineEntry) -> int | None:
        on_page = [line for line in self.lines if line.page == entry.page]
        if not on_page:
            later = next(
                (line for line in self.lines if line.page is not None and line.page > (entry.page or 0)), None
            )
            return later.index if later else None
        wanted = entry.title.casefold()
        _, bare_title = self._parse_chapter_title(entry.title)
        bare = bare_title.casefold()
        for line in on_page[:15]:
            text = line.text.casefold()
            if len(text) >= 3 and (text in wanted or wanted in text or (len(bare) >= 4 and bare in text)):
                return line.index
        return on_page[0].index

    def _chapter_heading_at(self, line: Line) -> tuple[int, str, set[int]] | None:
        """If this line starts a chapter, its number, title, and the lines used for the heading."""
        if line.on_contents_page:
            return None
        match = _CHAPTER.match(line.ascii)
        if not match:
            return None
        number = _parse_number(match.group("num"))
        rest = match.group("rest").strip(" -:.–—")
        if number is None or _looks_like_prose(rest):
            return None
        looks_like_heading = self._is_prominent(line) or match.group("word").isupper() or not self.has_layout
        if not looks_like_heading and rest:
            return None

        used = {line.index}
        title = rest
        if not title:
            # "Chapter 2" on its own line: the title is usually the next line (or the one before).
            for neighbour_index in (line.index + 1, line.index - 1):
                if 0 <= neighbour_index < len(self.lines):
                    neighbour = self.lines[neighbour_index]
                    if neighbour.page == line.page and self._could_be_title(neighbour):
                        title = neighbour.text
                        used.add(neighbour_index)
                        break
        if not looks_like_heading and not title:
            return None  # a plain "Chapter 5." line inside running text
        return number, (title or f"Chapter {number}")[:300], used

    def _could_be_title(self, line: Line) -> bool:
        words = line.text.split()
        if not words or len(words) > _MAX_TITLE_WORDS or letter_count(line.text) < 3:
            return False
        if self._marker_kind(line) is not None or _CHAPTER.match(line.ascii):
            return False
        if line.text.endswith((".", ",", ";")):
            return False
        return self._is_prominent(line) or not self.has_layout

    def _spans_from_headings(self) -> list[_Span]:
        spans: list[_Span] = []
        seen_numbers: set[int] = set()
        for line in self.lines:
            heading = self._chapter_heading_at(line)
            if heading is not None:
                number, title, used = heading
                # A chapter number seen before is a running header, or a heading inside the answer key.
                if number in seen_numbers:
                    continue
                seen_numbers.add(number)
                spans.append(
                    _Span(
                        start=line.index,
                        chapter=DetectedChapter(number, title, "heading"),
                        heading_lines=used,
                    )
                )
            elif spans and not line.on_contents_page and _MATTER.match(line.text) and self._is_strong(line):
                spans.append(_Span(start=line.index, chapter=None))
        return spans

    def _spans_from_heading_styles(self) -> list[_Span]:
        """Word / Markdown documents whose chapters are "Heading 1" without the word "Chapter"."""
        level_one = [line for line in self.lines if line.heading_level == 1 and not line.on_contents_page]
        if len(level_one) < 2:
            return []
        spans = []
        for line in level_one:
            if _MATTER.match(line.text):
                spans.append(_Span(start=line.index, chapter=None))
                continue
            number, title = self._parse_chapter_title(line.text)
            spans.append(
                _Span(
                    start=line.index,
                    chapter=DetectedChapter(number, title[:300], "heading"),
                    heading_lines={line.index},
                )
            )
        return spans

    def _whole_file_span(self) -> _Span:
        """No chapter headings: the whole file is one chapter (one NCERT PDF per chapter)."""
        number = chapter_number_from_filename(self.filename)
        title, used = None, set()
        for line in self.lines[:40]:
            if line.heading_level in (0, 1) and self._could_be_title(line):
                title, used = line.text, {line.index}
                break
        if title is None and self.body_size is not None:
            first_page = [
                line for line in self.lines if line.page == (self.lines[0].page if self.lines else None)
            ]
            big = [
                line
                for line in first_page
                if line.size and line.size >= self.body_size * 1.3 and self._could_be_title(line)
            ]
            if big:
                best = max(big, key=lambda line: line.size or 0)
                title, used = best.text, {best.index}
        chapter = DetectedChapter(number, (title or _title_from_filename(self.filename))[:300], "file")
        return _Span(start=0, chapter=chapter, heading_lines=used)

    def _set_chapter_pages(self) -> None:
        for position, span in enumerate(self.spans):
            if span.chapter is None:
                continue
            end = self.spans[position + 1].start if position + 1 < len(self.spans) else len(self.lines)
            pages = [line.page for line in self.lines[span.start : end] if line.page is not None]
            span.chapter.page_start = pages[0] if pages else None
            span.chapter.page_end = pages[-1] if pages else None

    def _span_ranges(self) -> list[tuple[_Span, int, int]]:
        ranges = []
        if self.spans and self.spans[0].start > 0:
            ranges.append((_Span(start=0, chapter=None), 0, self.spans[0].start))  # front matter
        for position, span in enumerate(self.spans):
            end = self.spans[position + 1].start if position + 1 < len(self.spans) else len(self.lines)
            ranges.append((span, span.start, end))
        return ranges

    # ---- step 2: exercises, questions, examples, summaries

    def _marker_kind(self, line: Line) -> _Marker | None:
        text = line.ascii
        exercise = _EXERCISE.match(text)
        if exercise:
            word = exercise.group("word").casefold()
            number = exercise.group("num")
            if word.startswith(("ex.",)) and not number:
                return None
            if "question" in word and not self._is_prominent(line):
                return None
            if not number and self.has_layout and not (self._is_prominent(line) or line.text.isupper()):
                return None
            return _Marker("exercise", number)
        example = _EXAMPLE.match(text)
        if example:
            rest = example.group("rest")
            if rest and rest[0].islower():
                return None  # "Example 3 shows that..." is a sentence
            return _Marker("example", example.group("num"))
        if _SUMMARY.match(text):
            return _Marker("summary")
        if _ANSWERS.match(text) and (self._is_prominent(line) or not self.has_layout):
            return _Marker("answers")
        return None

    def detect_exercises(self) -> None:
        self.markers = {}
        for span, start, end in self._span_ranges():
            if span.chapter is None:
                continue
            for line in self.lines[start:end]:
                if line.index in span.heading_lines or line.on_contents_page:
                    continue
                marker = self._marker_kind(line)
                if marker is not None:
                    self.markers[line.index] = marker

    # ---- step 3: topics, then assemble everything into segments

    def _numbered_topic(self, line: Line, chapter: DetectedChapter) -> tuple[str, str] | None:
        match = _NUMBERED_TOPIC.match(line.ascii)
        if not match:
            return None
        number, title = match.group("num"), match.group("title").strip()
        if chapter.number is not None and int(number.split(".")[0]) != chapter.number:
            return None
        words = title.split()
        if len(words) > _MAX_TITLE_WORDS or title.endswith((".", ",", ";", "=")) or letter_count(title) < 3:
            return None
        if not (title[0].isupper() or not title[0].isascii()):
            return None
        if self.has_layout and not self._is_prominent(line):
            return None
        return number, title

    def _unnumbered_topic(self, line: Line) -> str | None:
        words = line.text.split()
        if not words or len(words) > 10 or letter_count(line.text) < 4:
            return None
        if line.text.endswith((".", ",", ";", ":", "=")) or _NOT_A_TOPIC.match(line.text):
            return None
        if _QUESTION.match(line.ascii) or line.text[0] in "(-•*–":
            return None
        first = line.text[0]
        if not (first.isupper() or not first.isascii()):
            return None
        if line.heading_level is not None:
            return line.text
        if self._is_strong(line):
            return line.text
        # A short bold line on its own is a sub-heading; a long one is usually emphasised text.
        return line.text if line.bold and self.has_layout and len(words) <= 6 else None

    def detect_topics(self) -> DocumentStructure:
        segments: list[Segment] = []
        chapter_index = -1
        for span, start, end in self._span_ranges():
            if span.chapter is None:
                lines = self.lines[start:end]
                if lines:
                    segments.append(Segment(ContentType.OTHER, None, None, None, lines))
                continue
            chapter_index += 1
            segments.extend(self._chapter_segments(span, chapter_index, start, end))
        return DocumentStructure(chapters=self.chapters, segments=[s for s in segments if s.lines])

    def _chapter_segments(self, span: _Span, chapter_index: int, start: int, end: int) -> list[Segment]:
        chapter = span.chapter
        assert chapter is not None
        segments: list[Segment] = []
        mode: Literal["concept", "example", "exercise", "summary", "other"] = "concept"
        topic: int | None = None
        exercise: int | None = None
        current: Segment | None = None
        last_question = 0
        preamble: list[Line] = []
        solution_seen = False
        example_tail = 0

        def open_segment(kind: ContentType, **meta: str) -> Segment:
            nonlocal current
            current = Segment(kind, chapter_index, topic, exercise, meta={k: v for k, v in meta.items() if v})
            segments.append(current)
            return current

        def close_exercise() -> None:
            nonlocal exercise, preamble
            if exercise is not None:
                ex = chapter.exercises[exercise]
                if ex.question_count == 0 and preamble:
                    # No numbered questions were found: keep the whole block as one question.
                    segment = open_segment(ContentType.EXERCISE_QUESTION)
                    segment.lines.extend(preamble)
                    ex.question_count = 1
            exercise, preamble = None, []

        def leave_to_concept() -> None:
            nonlocal mode, current
            close_exercise()
            mode, current = "concept", None

        for line in self.lines[start:end]:
            if line.on_contents_page:
                continue
            is_heading_line = line.index in span.heading_lines
            marker = None if is_heading_line else self.markers.get(line.index)

            # ---- headings that start something new
            if not is_heading_line and marker is None:
                numbered = self._numbered_topic(line, chapter)
                # Unnumbered headings only count where they cannot be part of an example or a
                # question: bold words inside a worked example are not a new topic.
                may_start_topic = (
                    mode in ("concept", "summary", "other")
                    or (mode == "example" and solution_seen)
                    or (mode == "exercise" and last_question > 0 and self._is_strong(line))
                )
                unnumbered = self._unnumbered_topic(line) if numbered is None and may_start_topic else None
                if numbered or unnumbered:
                    leave_to_concept()
                    number, title = numbered if numbered else (None, unnumbered or "")
                    chapter.topics.append(DetectedTopic(number, title[:300], line.page))
                    topic = len(chapter.topics) - 1
                    open_segment(ContentType.CONCEPT).lines.append(line)
                    continue

            if marker is not None:
                close_exercise()
                if marker.kind == "exercise":
                    chapter.exercises.append(DetectedExercise(marker.number or "", line.page, line.page))
                    exercise = len(chapter.exercises) - 1
                    mode, current, last_question, preamble = "exercise", None, 0, []
                    continue  # the "EXERCISE 2.3" line itself is a label, not content
                if marker.kind == "example":
                    mode, solution_seen, example_tail = "example", False, 0
                    open_segment(ContentType.EXAMPLE, example_number=marker.number or "").lines.append(line)
                    continue
                if marker.kind == "summary":
                    mode, topic = "summary", None
                    open_segment(ContentType.SUMMARY).lines.append(line)
                    continue
                mode = "other"  # answers
                open_segment(ContentType.OTHER).lines.append(line)
                continue

            # ---- ordinary lines
            if mode == "exercise":
                assert exercise is not None
                ex = chapter.exercises[exercise]
                ex.page_end = line.page if line.page is not None else ex.page_end
                number = self._question_number(line)
                if number is not None and (last_question == 0 or number == last_question + 1):
                    last_question = number
                    ex.question_count += 1
                    segment = open_segment(ContentType.EXERCISE_QUESTION, question_number=str(number))
                    if preamble:
                        # The instructions before question 1 belong to every question ("Solve the
                        # following equations."). A long passage (a case study) goes with question 1 only.
                        instructions = " ".join(item.text for item in preamble)
                        segment.meta["instructions"] = instructions[:500]
                        segment.lines.extend(preamble)
                        if len(instructions.split()) > _MAX_SHARED_INSTRUCTION_WORDS:
                            preamble = []
                    segment.lines.append(line)
                elif current is None:
                    preamble.append(line)
                else:
                    current.lines.append(line)
                continue

            if mode == "example":
                assert current is not None
                if _SOLUTION.match(line.text):
                    solution_seen = True
                elif solution_seen:
                    example_tail += len(line.text) // 4
                    # A long run of text after the solution is the book moving on, not the example.
                    previous = current.lines[-1].text if current.lines else ""
                    if example_tail > _EXAMPLE_TAIL_TOKENS and previous.endswith((".", "।", "?", "!")):
                        mode = "concept"
                        open_segment(ContentType.CONCEPT).lines.append(line)
                        continue
                current.lines.append(line)
                continue

            kind = _MODE_CONTENT_TYPE[mode]
            if current is None or current.kind is not kind:
                open_segment(kind)
            assert current is not None
            current.lines.append(line)

        close_exercise()
        # A segment made only of the chapter heading carries no knowledge: every chunk's label
        # already names its chapter.
        return [
            segment
            for segment in segments
            if any(line.index not in span.heading_lines for line in segment.lines)
        ]

    @staticmethod
    def _question_number(line: Line) -> int | None:
        match = _QUESTION.match(line.ascii) or _QUESTION_PREFIXED.match(line.ascii)
        if not match:
            return None
        number = int(match.group("num"))
        return number if 0 < number < 500 else None
