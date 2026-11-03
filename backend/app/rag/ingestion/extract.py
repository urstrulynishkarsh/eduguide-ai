"""Stage 2 - read the text, page by page.

* PDF: text with font size and weight per line (headings are found through them), plus the PDF's
  own outline (bookmarks). Pages without usable text are sent to OCR when it is configured.
* DOCX: paragraphs and tables in reading order; heading styles become heading levels. Page numbers
  are known only when Word saved its page breaks into the file.
* TXT: lines; a form-feed character starts a new page.

The blocking work runs in a worker thread; OCR calls are awaited one page at a time.
"""

import asyncio
import ctypes
import io
import logging
import re
from collections.abc import Iterator

import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_c
from docx import Document as open_docx
from docx.table import Table
from docx.text.paragraph import Paragraph

from app.core.enums import FileKind
from app.rag.ingestion.errors import ProcessingError
from app.rag.ingestion.file_checks import decode_text_file
from app.rag.ingestion.pdf_lock import PDFIUM_LOCK
from app.rag.ingestion.text_quality import normalize_line, page_needs_ocr
from app.rag.ingestion.types import ExtractedDocument, OutlineEntry, PageText, TextLine
from app.rag.ocr import OCRError, OCRProvider

logger = logging.getLogger(__name__)

_LINE_BREAK = re.compile(r"\r\n|\r|\n")
_BOLD_WEIGHT = 600
_SAMPLED_CHARS_PER_LINE = 8
_OCR_SCALE = 300 / 72  # render at 300 dpi; good OCR needs it


# ---------------------------------------------------------------------------- PDF


_BOLD_NAME = re.compile(rb"bold|black|heavy|semibold|demi", re.IGNORECASE)
_FORCE_BOLD_FLAG = 1 << 18


def _char_is_bold(textpage: pdfium.PdfTextPage, index: int) -> bool:
    weight = pdfium_c.FPDFText_GetFontWeight(textpage, index)
    if weight > 0:
        return weight >= _BOLD_WEIGHT
    # Standard fonts (Helvetica-Bold...) carry no weight; their name and flags still tell.
    flags = ctypes.c_int()
    length = pdfium_c.FPDFText_GetFontInfo(textpage, index, None, 0, ctypes.byref(flags))
    if length <= 0:
        return False
    name = ctypes.create_string_buffer(length)
    pdfium_c.FPDFText_GetFontInfo(textpage, index, name, length, ctypes.byref(flags))
    return bool(flags.value & _FORCE_BOLD_FLAG) or bool(_BOLD_NAME.search(name.value))


def _line_style(textpage: pdfium.PdfTextPage, start: int, line: str) -> tuple[float | None, bool]:
    """Font size and boldness of a line, sampled from its first few visible characters."""
    sizes: list[float] = []
    bold = 0
    for offset, char in enumerate(line):
        if char.isspace():
            continue
        index = start + offset
        sizes.append(pdfium_c.FPDFText_GetFontSize(textpage, index))
        if _char_is_bold(textpage, index):
            bold += 1
        if len(sizes) >= _SAMPLED_CHARS_PER_LINE:
            break
    if not sizes:
        return None, False
    return round(max(sizes), 1), bold * 2 > len(sizes)


def _pdf_page_lines(page: pdfium.PdfPage) -> list[TextLine]:
    textpage = page.get_textpage()
    try:
        text = textpage.get_text_range()
        # Character indexes match string positions unless the page uses characters outside the
        # Basic Multilingual Plane; then styles are skipped rather than guessed.
        styled = len(text) == textpage.count_chars()
        lines: list[TextLine] = []
        position = 0
        for raw_line, separator in _split_keeping_offsets(text):
            line = normalize_line(raw_line)
            if line:
                size, bold = _line_style(textpage, position, raw_line) if styled else (None, False)
                lines.append(TextLine(text=line, size=size, bold=bold))
            position += len(raw_line) + len(separator)
        return lines
    finally:
        textpage.close()


def _split_keeping_offsets(text: str) -> Iterator[tuple[str, str]]:
    position = 0
    for match in _LINE_BREAK.finditer(text):
        yield text[position : match.start()], match.group()
        position = match.end()
    yield text[position:], ""


def _pdf_outline(pdf: pdfium.PdfDocument) -> list[OutlineEntry]:
    entries: list[OutlineEntry] = []
    try:
        for bookmark in pdf.get_toc(max_depth=4):
            title = normalize_line(bookmark.get_title() or "")
            destination = bookmark.get_dest()
            page_index = destination.get_index() if destination is not None else None
            if title:
                entries.append(
                    OutlineEntry(
                        title=title,
                        level=bookmark.level,
                        page=page_index + 1 if page_index is not None else None,
                    )
                )
    except pdfium.PdfiumError:
        logger.info("PDF outline could not be read; continuing without it")
        return []
    return entries


def _extract_pdf_sync(data: bytes) -> tuple[ExtractedDocument, list[int]]:
    """Text of every page, plus the 0-based indexes of pages that need OCR."""
    with PDFIUM_LOCK:
        try:
            pdf = pdfium.PdfDocument(data)
        except pdfium.PdfiumError:
            raise ProcessingError("file_unreadable") from None
        try:
            pages: list[PageText] = []
            needs_ocr: list[int] = []
            for index in range(len(pdf)):
                page = pdf[index]
                try:
                    lines = _pdf_page_lines(page)
                finally:
                    page.close()
                if page_needs_ocr("\n".join(line.text for line in lines)):
                    needs_ocr.append(index)
                    pages.append(PageText(number=index + 1, lines=lines, source="none"))
                else:
                    pages.append(PageText(number=index + 1, lines=lines))
            outline = _pdf_outline(pdf)
            return ExtractedDocument(pages=pages, outline=outline, page_count=len(pdf)), needs_ocr
        finally:
            pdf.close()


def _render_page_png(data: bytes, index: int) -> bytes:
    with PDFIUM_LOCK:
        pdf = pdfium.PdfDocument(data)
        try:
            page = pdf[index]
            try:
                image = page.render(scale=_OCR_SCALE, grayscale=True).to_pil()
            finally:
                page.close()
        finally:
            pdf.close()
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


async def _extract_pdf(data: bytes, ocr: OCRProvider | None, ocr_languages: list[str]) -> ExtractedDocument:
    document, needs_ocr = await asyncio.to_thread(_extract_pdf_sync, data)
    for index in needs_ocr:
        page = document.pages[index]
        if ocr is None:
            document.unreadable_pages += 1
            continue
        try:
            image = await asyncio.to_thread(_render_page_png, data, index)
            result = await ocr.read_page(image, languages=ocr_languages)
        except OCRError:
            logger.warning("OCR failed on page %d", index + 1, exc_info=True)
            document.unreadable_pages += 1
            continue
        lines = [TextLine(text=text) for raw in result.lines if (text := normalize_line(raw))]
        if lines:
            page.lines, page.source = lines, "ocr"
            document.ocr_pages += 1
        else:
            document.unreadable_pages += 1
    return document


# ---------------------------------------------------------------------------- DOCX

_HEADING_STYLE = re.compile(r"^heading\s*(\d)$", re.IGNORECASE)


def _heading_level(paragraph: Paragraph) -> int | None:
    name = (paragraph.style.name if paragraph.style is not None else "") or ""
    if name.lower() == "title":
        return 0
    match = _HEADING_STYLE.match(name.strip())
    return int(match.group(1)) if match else None


def _paragraph_is_bold(paragraph: Paragraph) -> bool:
    runs = [run for run in paragraph.runs if run.text.strip()]
    return bool(runs) and all(run.bold for run in runs)


def _extract_docx_sync(data: bytes) -> ExtractedDocument:
    try:
        document = open_docx(io.BytesIO(data))
    except Exception:  # python-docx raises many different errors for damaged files
        raise ProcessingError("file_unreadable") from None

    # Page numbers only exist if Word wrote its rendered page breaks into the file.
    page_number = 1
    has_page_breaks = False
    pages: list[PageText] = [PageText(number=1)]

    def add(text: str, **style: object) -> None:
        line = normalize_line(text)
        if line:
            pages[-1].lines.append(TextLine(text=line, **style))  # type: ignore[arg-type]

    for block in document.iter_inner_content():
        if isinstance(block, Paragraph):
            breaks = len(block.rendered_page_breaks)
            if breaks:
                has_page_breaks = True
                page_number += breaks
                pages.append(PageText(number=page_number))
            add(block.text, heading_level=_heading_level(block), bold=_paragraph_is_bold(block))
        elif isinstance(block, Table):
            for row in block.rows:
                cells: list[str] = []
                for cell in row.cells:
                    text = " ".join(cell.text.split())
                    if text and (not cells or cells[-1] != text):  # merged cells repeat their text
                        cells.append(text)
                add(" | ".join(cells))

    if not has_page_breaks:
        merged = PageText(number=None, lines=[line for page in pages for line in page.lines])
        return ExtractedDocument(pages=[merged])
    return ExtractedDocument(pages=[page for page in pages if page.lines], page_count=page_number)


# ---------------------------------------------------------------------------- TXT


_MARKDOWN_HEADING = re.compile(r"^(#{1,6})\s+(\S.*)$")


def _text_line(line: str) -> TextLine:
    """Notes written in Markdown mark headings with #: "# Chapter 1", "## 1.1 Fractions"."""
    match = _MARKDOWN_HEADING.match(line)
    if match:
        return TextLine(text=match.group(2).rstrip(" #"), heading_level=len(match.group(1)))
    return TextLine(text=line)


def _extract_txt_sync(data: bytes) -> ExtractedDocument:
    try:
        text = decode_text_file(data)
    except Exception:
        raise ProcessingError("file_unreadable") from None
    parts = text.split("\f")
    numbered = len(parts) > 1
    pages = [
        PageText(
            number=index + 1 if numbered else None,
            lines=[_text_line(line) for raw in _LINE_BREAK.split(part) if (line := normalize_line(raw))],
        )
        for index, part in enumerate(parts)
    ]
    return ExtractedDocument(pages=pages, page_count=len(pages) if numbered else None)


# ---------------------------------------------------------------------------- entry point


async def extract_document(
    data: bytes, kind: FileKind, *, ocr: OCRProvider | None, ocr_languages: list[str]
) -> ExtractedDocument:
    if kind is FileKind.PDF:
        return await _extract_pdf(data, ocr, ocr_languages)
    if kind is FileKind.DOCX:
        return await asyncio.to_thread(_extract_docx_sync, data)
    return await asyncio.to_thread(_extract_txt_sync, data)
