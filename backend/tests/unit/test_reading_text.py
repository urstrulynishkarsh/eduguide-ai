"""Stage 2: reading text, recognising scripts and pages that need OCR, removing page furniture."""

import pytest

from app.core.enums import FileKind
from app.rag.ingestion.cleanup import is_page_number, remove_page_furniture
from app.rag.ingestion.extract import extract_document
from app.rag.ingestion.text_quality import (
    detect_language,
    estimate_tokens,
    looks_like_legacy_font,
    normalize_line,
    page_needs_ocr,
    to_ascii_digits,
)
from app.rag.ingestion.types import PageText, TextLine
from tests.fakes import FakeOCR
from tests.samples import NOTES_TEXT, make_docx, make_pdf, make_scanned_pdf


def test_normalize_line_keeps_devanagari_joiners_and_drops_noise():
    assert normalize_line("  Linear   Equa­tions\t ") == "Linear Equations"
    assert normalize_line("क्‍ष") == "क्‍ष"  # zero-width joiner changes how Hindi is written
    assert to_ascii_digits("प्रश्नावली २.३") == "प्रश्नावली 2.3"


def test_language_of_a_piece_of_text():
    assert detect_language("जब किसी पूरी चीज़ को बराबर भागों में बाँटते हैं", default="en") == "hi"
    assert detect_language("Rational numbers are closed under addition", default="hi") == "en"
    assert detect_language("2/3 + 4/3 = 2", default="hi") == "hi"  # no letters: the book's language


def test_legacy_hindi_fonts_are_recognised_as_unreadable():
    # How a Kruti Dev page comes out of a PDF: Devanagari stored as Latin letters and symbols.
    kruti_dev = (
        "Hkkjr ,d d`f\"k iz/kku ns'k gS A ;gk¡ dh vf/kdka'k turk xk¡oksa esa jgrh gS rFkk mudk eq[; "
        "O;olk; Ñf\"k gS A xk¡oksa esa yksx [ksrh djrs gSa vkSj i'kq ikyrs gSa"
    )
    english = (
        "India is a country where most people live in villages. They grow crops, keep animals and "
        "sell what they make in the market. Children often help their parents after school."
    )
    assert looks_like_legacy_font(kruti_dev)
    assert page_needs_ocr(kruti_dev)
    assert not looks_like_legacy_font(english)
    assert not page_needs_ocr(english)
    assert page_needs_ocr("12")  # an image-only page has at most a page number


def test_token_estimate_counts_hindi_as_more_expensive():
    english, hindi = "the water cycle " * 20, "जल चक्र " * 20
    assert estimate_tokens(hindi) > estimate_tokens(english) * 0.8
    assert estimate_tokens("x") == 1


@pytest.mark.parametrize("text", ["12", "- 12 -", "Page 4", "page 3 of 9", "vii", "४५"])
def test_page_numbers(text: str):
    assert is_page_number(text)


@pytest.mark.parametrize("text", ["(i)", "1. Solve x + 2 = 5", "Chapter 2", "2x + 3"])
def test_not_page_numbers(text: str):
    assert not is_page_number(text)


_SENTENCES = [
    "An equation is a statement that two expressions are equal.",
    "To solve it we do the same operation on both sides.",
    "Subtracting the same number from both sides keeps them equal.",
    "Dividing both sides by the same non-zero number also keeps them equal.",
    "We can check the answer by putting it back into the equation.",
]


def test_running_headers_and_page_numbers_are_removed_but_headings_kept():
    pages = [
        PageText(
            number=page,
            lines=[
                TextLine("Mathematics", size=9),
                *([TextLine("Linear Equations", size=22)] if page == 1 else []),
                TextLine(_SENTENCES[page - 1], size=11),
                TextLine(str(page), size=9),
            ],
        )
        for page in range(1, 6)
    ]
    # The chapter title is also the (small) running header on the later pages.
    for page in pages[1:]:
        page.lines.insert(0, TextLine("Linear Equations", size=9))

    remove_page_furniture(pages)

    # Gone: "Mathematics", the page numbers and the small running headers.
    assert [line.text for line in pages[0].lines] == ["Linear Equations", _SENTENCES[0]]
    assert [line.text for line in pages[3].lines] == [_SENTENCES[3]]


async def test_pdf_lines_keep_font_size_and_weight():
    document = await extract_document(make_pdf(), FileKind.PDF, ocr=None, ocr_languages=["eng"])

    assert document.page_count == 4
    assert document.ocr_pages == document.unreadable_pages == 0
    first_page = {line.text: line for line in document.pages[0].lines}
    assert first_page["Rational Numbers"].size == 22
    assert first_page["Rational Numbers"].bold
    assert first_page["1.1 Introduction"].bold
    assert first_page["Chapter 1"].size == 13
    assert not first_page["Chapter 1"].bold


async def test_pdf_outline_is_read():
    data = make_pdf(outline=[("Chapter 1 Rational Numbers", 0), ("Chapter 2 Linear Equations", 2)])
    document = await extract_document(data, FileKind.PDF, ocr=None, ocr_languages=["eng"])
    assert [(entry.title, entry.page) for entry in document.outline] == [
        ("Chapter 1 Rational Numbers", 1),
        ("Chapter 2 Linear Equations", 3),
    ]


async def test_scanned_pages_without_ocr_are_counted_as_unreadable():
    document = await extract_document(make_scanned_pdf(2), FileKind.PDF, ocr=None, ocr_languages=["eng"])
    assert document.unreadable_pages == 2
    assert all(not page.lines and page.source == "none" for page in document.pages)


async def test_scanned_pages_go_to_ocr_with_the_book_language_first():
    ocr = FakeOCR()
    document = await extract_document(
        make_scanned_pdf(2), FileKind.PDF, ocr=ocr, ocr_languages=["hin", "eng"]
    )

    assert document.ocr_pages == 2
    assert [page.source for page in document.pages] == ["ocr", "ocr"]
    assert document.pages[0].lines[1].text == "Our Environment"
    assert len(ocr.calls) == 2
    image_size, languages = ocr.calls[0]
    assert image_size > 1000  # a real rendered page image
    assert languages == ("hin", "eng")


async def test_failed_ocr_leaves_the_page_unreadable():
    document = await extract_document(
        make_scanned_pdf(1), FileKind.PDF, ocr=FakeOCR(fail=True), ocr_languages=["eng"]
    )
    assert document.unreadable_pages == 1
    assert document.ocr_pages == 0


async def test_docx_paragraphs_headings_and_tables():
    document = await extract_document(make_docx(), FileKind.DOCX, ocr=None, ocr_languages=["eng"])
    lines = document.pages[0].lines
    assert document.pages[0].number is None  # Word did not save page breaks
    assert (lines[0].text, lines[0].heading_level) == ("Science Notes", 0)
    assert (lines[1].text, lines[1].heading_level) == ("Chapter 3 Plants and Animals", 1)
    assert "Root | Takes in water" in [line.text for line in lines]


async def test_text_files_understand_markdown_headings_and_form_feeds():
    document = await extract_document(NOTES_TEXT.encode(), FileKind.TXT, ocr=None, ocr_languages=["eng"])
    assert (document.pages[0].lines[0].text, document.pages[0].lines[0].heading_level) == (
        "Chapter 5 The Water Cycle",
        1,
    )

    paged = await extract_document(b"Page one text\fPage two text", FileKind.TXT, ocr=None, ocr_languages=[])
    assert [page.number for page in paged.pages] == [1, 2]
