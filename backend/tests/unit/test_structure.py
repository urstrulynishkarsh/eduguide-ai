"""Stage 3: finding chapters, topics, exercises, examples, questions and summaries."""

from app.core.enums import ContentType, FileKind
from app.rag.ingestion.cleanup import remove_page_furniture
from app.rag.ingestion.extract import extract_document
from app.rag.ingestion.labels import exercise_title
from app.rag.ingestion.structure import (
    DocumentStructure,
    StructureDetector,
    chapter_number_from_filename,
    roman_to_int,
)
from app.rag.ingestion.types import OutlineEntry, PageText, TextLine
from tests.samples import HINDI_TEXT, NOTES_TEXT, make_docx, make_pdf


def detect_structure(
    pages: list[PageText], *, outline: list[OutlineEntry], filename: str, question_paper: bool = False
) -> DocumentStructure:
    """The three detection steps in the order the pipeline runs them."""
    detector = StructureDetector(pages, outline=outline, filename=filename, question_paper=question_paper)
    detector.detect_chapters()
    detector.detect_exercises()
    return detector.detect_topics()


async def _structure(data: bytes, kind: FileKind, filename: str = "book.pdf") -> DocumentStructure:
    document = await extract_document(data, kind, ocr=None, ocr_languages=["eng"])
    remove_page_furniture(document.pages)
    return detect_structure(document.pages, outline=document.outline, filename=filename)


def _plain(*texts: str, page: int | None = None) -> list[PageText]:
    """A text file's worth of lines, without any layout information."""
    return [PageText(number=page, lines=[TextLine(text) for text in texts])]


def _kinds(structure: DocumentStructure) -> list[str]:
    return [segment.kind.value for segment in structure.segments]


async def test_textbook_pdf_chapters_topics_exercises_and_questions():
    structure = await _structure(make_pdf(), FileKind.PDF)

    assert [(c.number, c.title, c.page_start, c.page_end) for c in structure.chapters] == [
        (1, "Rational Numbers", 1, 2),
        (2, "Linear Equations in One Variable", 3, 4),
    ]
    first, second = structure.chapters
    assert [(t.number, t.title) for t in first.topics] == [
        ("1.1", "Introduction"),
        ("1.2", "Properties of Rational Numbers"),
    ]
    assert [(e.label, e.question_count) for e in second.exercises] == [("2.1", 4), ("2.2", 2)]
    assert structure.example_count == 2
    assert all(c.detected_by == "heading" for c in structure.chapters)


async def test_one_question_is_one_segment_with_its_parts_and_instructions():
    structure = await _structure(make_pdf(), FileKind.PDF)
    questions = [s for s in structure.segments if s.kind is ContentType.EXERCISE_QUESTION]

    first_exercise = [q for q in questions if q.chapter == 0]
    assert [q.meta["question_number"] for q in first_exercise] == ["1", "2", "3"]
    # "(i) Write your answer..." belongs to question 2; the instructions are repeated on every question.
    assert [line.text for line in first_exercise[1].lines] == [
        "Find the value of each of the following.",
        "2. 5/8 - 3/8",
        "(i) Write your answer in the lowest terms.",
    ]
    assert first_exercise[2].meta["instructions"] == "Find the value of each of the following."
    # A question that wraps onto a second line stays one question.
    word_problem = next(q for q in questions if q.chapter == 1 and q.exercise == 1)
    assert [line.text for line in word_problem.lines][-1] == "What is the number?"


async def test_examples_and_summaries():
    structure = await _structure(make_pdf(), FileKind.PDF)
    example = next(s for s in structure.segments if s.kind is ContentType.EXAMPLE)
    assert example.meta == {"example_number": "1"}
    assert example.lines[-1].text == "3/7 + 2/7 = 5/7."
    summary = next(s for s in structure.segments if s.kind is ContentType.SUMMARY)
    assert summary.chapter == 0
    assert summary.topic is None


async def test_pdf_outline_is_used_when_present():
    data = make_pdf(outline=[("Chapter 1 Rational Numbers", 0), ("Chapter 2 Linear Equations", 2)])
    structure = await _structure(data, FileKind.PDF)
    assert [(c.number, c.title, c.detected_by) for c in structure.chapters] == [
        (1, "Rational Numbers", "outline"),
        (2, "Linear Equations", "outline"),
    ]
    # The heading lines are not mistaken for a topic.
    assert structure.chapters[0].topics[0].title == "Introduction"


async def test_word_notes_with_heading_styles():
    structure = await _structure(make_docx(), FileKind.DOCX, "science-notes.docx")
    assert [(c.number, c.title) for c in structure.chapters] == [(3, "Plants and Animals")]
    chapter = structure.chapters[0]
    assert [(t.number, t.title) for t in chapter.topics] == [("3.1", "Parts of a Plant")]
    assert [(e.label, e.question_count) for e in chapter.exercises] == [("", 2)]
    assert structure.segments[0].kind is ContentType.OTHER  # "Science Notes" comes before the chapter


async def test_hindi_book_patterns():
    structure = await _structure(HINDI_TEXT.encode(), FileKind.TXT, "hindi.txt")
    assert [(c.number, c.title) for c in structure.chapters] == [(4, "भिन्न")]
    chapter = structure.chapters[0]
    assert [(t.number, t.title) for t in chapter.topics] == [("4.1", "भिन्न क्या है")]
    assert [(e.label, e.question_count) for e in chapter.exercises] == [("4.1", 2)]
    assert structure.example_count == 1


async def test_markdown_notes():
    structure = await _structure(NOTES_TEXT.encode(), FileKind.TXT, "notes.txt")
    chapter = structure.chapters[0]
    assert (chapter.number, chapter.title) == (5, "The Water Cycle")
    assert [t.title for t in chapter.topics] == ["Evaporation", "Condensation"]
    assert chapter.exercises[0].question_count == 2


def test_a_file_without_chapter_headings_is_one_chapter_named_after_the_file():
    structure = detect_structure(
        _plain("Air is all around us.", "We cannot see air but we can feel it."),
        outline=[],
        filename="hesc106.pdf",  # NCERT file name: chapter 6
    )
    assert [(c.number, c.title, c.detected_by) for c in structure.chapters] == [(6, "hesc106", "file")]
    assert _kinds(structure) == ["concept"]


def test_sentences_that_start_with_chapter_are_not_headings():
    structure = detect_structure(
        _plain(
            "Chapter 1 Fractions",
            "Chapter 3 we learnt about decimals and how to add them carefully.",
            "Chapter 5.",
            "Some more text.",
        ),
        outline=[],
        filename="notes.txt",
    )
    assert [c.number for c in structure.chapters] == [1]


def test_running_headers_and_answer_keys_do_not_repeat_chapters():
    structure = detect_structure(
        _plain(
            "Chapter 1 Fractions",
            "A fraction is a part of a whole.",
            "Chapter 1 Fractions",  # running header that survived cleaning
            "More about fractions.",
            "Chapter 2 Decimals",
            "A decimal is another way to write a fraction.",
            "ANSWERS",
            "Chapter 1",
            "1. 3/4",
        ),
        outline=[],
        filename="maths.txt",
    )
    assert [(c.number, c.title) for c in structure.chapters] == [(1, "Fractions"), (2, "Decimals")]
    assert structure.segments[-1].kind is ContentType.OTHER  # the answer key is not chapter 2's text


def test_contents_page_is_not_mistaken_for_chapters():
    pages = [
        PageText(
            number=1,
            lines=[
                TextLine("Contents"),
                TextLine("Chapter 1 Fractions ........ 1"),
                TextLine("Chapter 2 Decimals ........ 9"),
            ],
        ),
        PageText(
            number=2, lines=[TextLine("Chapter 1 Fractions"), TextLine("A fraction is a part of a whole.")]
        ),
    ]
    structure = detect_structure(pages, outline=[], filename="maths.pdf")
    assert [(c.number, c.page_start) for c in structure.chapters] == [(1, 2)]
    assert structure.segments[0].kind is ContentType.OTHER


def test_decimal_numbers_are_not_question_numbers():
    structure = detect_structure(
        _plain(
            "Chapter 1 Measures",
            "Exercise 1.1",
            "1. A bag has rice.",
            "2.5 kg of it is used. How much is left?",
            "2. Convert 3 m to cm.",
        ),
        outline=[],
        filename="m.txt",
    )
    exercise = structure.chapters[0].exercises[0]
    assert exercise.question_count == 2
    first = next(s for s in structure.segments if s.meta.get("question_number") == "1")
    assert first.lines[-1].text == "2.5 kg of it is used. How much is left?"


def test_topic_numbers_must_belong_to_the_chapter():
    structure = detect_structure(
        _plain("Chapter 2 Equations", "2.1 Introduction", "Some text.", "3.14 Is The Value Of Pi", "More."),
        outline=[],
        filename="m.txt",
    )
    assert [t.number for t in structure.chapters[0].topics] == ["2.1"]


def test_long_case_study_goes_with_the_first_question_only():
    case = " ".join(["The school garden has many plants and the children water them daily."] * 5)
    structure = detect_structure(
        _plain("Chapter 1 Plants", "Exercises", case, "1. Name two plants.", "2. Why do plants need water?"),
        outline=[],
        filename="s.txt",
    )
    questions = [s for s in structure.segments if s.kind is ContentType.EXERCISE_QUESTION]
    assert len(questions[0].lines) == 2
    assert len(questions[1].lines) == 1


def test_bold_words_inside_a_worked_example_do_not_start_a_topic():
    pages = [
        PageText(
            number=1,
            lines=[
                TextLine("Chapter 1 Fractions", size=20, bold=True),
                TextLine("Fractions are parts of a whole.", size=11),
                TextLine("Example 1: Add 1/4 and 2/4.", size=11),
                TextLine("Same Denominator", size=11, bold=True),
                TextLine("We add the numerators: 3/4.", size=11),
            ],
        )
    ]
    structure = detect_structure(pages, outline=[], filename="f.pdf")
    assert structure.chapters[0].topics == []
    example = next(s for s in structure.segments if s.kind is ContentType.EXAMPLE)
    assert [line.text for line in example.lines][-1] == "We add the numerators: 3/4."


def test_outline_with_front_matter():
    pages = [
        PageText(number=1, lines=[TextLine("Foreword"), TextLine("This book was written for children.")]),
        PageText(number=2, lines=[TextLine("Fractions"), TextLine("A fraction is a part of a whole.")]),
        PageText(number=3, lines=[TextLine("Decimals"), TextLine("A decimal has a point.")]),
    ]
    outline = [
        OutlineEntry("Foreword", 0, 1),
        OutlineEntry("1. Fractions", 0, 2),
        OutlineEntry("2. Decimals", 0, 3),
    ]
    structure = detect_structure(pages, outline=outline, filename="book.pdf")
    assert [(c.number, c.title, c.page_start) for c in structure.chapters] == [
        (1, "Fractions", 2),
        (2, "Decimals", 3),
    ]
    assert structure.segments[0].kind is ContentType.OTHER
    assert structure.segments[0].chapter is None


def test_bookmarks_that_are_only_a_number_are_the_chapters_numbers():
    pages = [
        PageText(
            number=1,
            lines=[TextLine("Chapter 1"), TextLine("Knowing Our Numbers"), TextLine("We count every day.")],
        ),
        PageText(number=2, lines=[TextLine("Whole Numbers"), TextLine("Zero is a whole number.")]),
    ]
    outline = [OutlineEntry("1", 0, 1), OutlineEntry(" II ", 0, 2)]
    structure = detect_structure(pages, outline=outline, filename="book.pdf")
    # The page's heading names the first; the second page has none.
    assert [(c.number, c.title, c.detected_by) for c in structure.chapters] == [
        (1, "Knowing Our Numbers", "outline"),
        (2, "Chapter 2", "outline"),
    ]


def test_helpers():
    assert roman_to_int("IV") == 4
    assert roman_to_int("XII") == 12
    assert roman_to_int("IIII") is None
    assert chapter_number_from_filename("jemh104.pdf") == 4
    assert chapter_number_from_filename("Science Chapter 7 notes.docx") == 7
    assert chapter_number_from_filename("my notes.pdf") is None


# ------------------------------------------------------------------ question papers


def _paper(*texts: str, filename: str = "CBSE-2023-Maths.pdf") -> DocumentStructure:
    return detect_structure(_plain(*texts), outline=[], filename=filename, question_paper=True)


def _questions(structure: DocumentStructure) -> list[tuple[str, str]]:
    """(the section's label, the question's text) of every question, in order."""
    (chapter,) = structure.chapters
    return [
        (chapter.exercises[s.exercise].label, " ".join(line.text for line in s.lines))
        for s in structure.segments
        if s.kind is ContentType.EXERCISE_QUESTION and s.exercise is not None
    ]


def test_a_question_paper_is_one_chapter_of_sections_and_questions():
    structure = _paper(
        "CBSE Class X Mathematics (Standard)",
        "Time Allowed: 3 hours Maximum Marks: 80",
        "General Instructions:",
        "1. This question paper has 5 sections A-E.",
        "2. Section A has 20 MCQs carrying 1 mark each.",
        "SECTION A",
        "Section A consists of 20 questions of 1 mark each.",
        "1. If HCF (65, 117) = 65m - 117, then m is",
        "(a) 4 (b) 2 (c) 1 (d) 3",
        "2. The roots of x^2 - 4 = 0 are",
        "SECTION - B",
        "3. Find the zeroes of x^2 - 3x + 2. [2]",
        "4. Prove that root 2 is irrational. [2]",
        "OR",
        "Show that 5 - root 3 is irrational.",
        "Section C (3 marks each)",
        "5. A train covers 360 km at a uniform speed. Find its speed.",
    )
    (chapter,) = structure.chapters
    # Named after the file: every year's paper has the same heading. A year is not a chapter number.
    assert (chapter.number, chapter.title, chapter.topics) == (None, "CBSE 2023 Maths", [])
    assert [(e.label, e.question_count) for e in chapter.exercises] == [
        ("Section A", 2),
        ("Section B", 2),
        ("Section C (3 marks each)", 1),
    ]
    questions = _questions(structure)
    # The section's instruction goes with each of its questions; "OR" stays inside its question.
    assert questions[0][1].startswith("Section A consists of 20 questions of 1 mark each. 1. If HCF")
    assert questions[3] == (
        "Section B",
        "4. Prove that root 2 is irrational. [2] OR Show that 5 - root 3 is irrational.",
    )
    # The front page and the numbered instructions are not questions, nor teaching text.
    assert structure.segments[0].kind is ContentType.OTHER
    assert "Maximum Marks: 80" in " ".join(line.text for line in structure.segments[0].lines)


def test_a_paper_in_parts_names_each_section_after_its_part():
    structure = _paper(
        "JEE Main 2024 Paper 1",
        "PART A - PHYSICS",
        "SECTION A",
        "1. A ball is thrown up at 20 m/s. Its greatest height is (1) 10 m (2) 20 m (3) 30 m (4) 40 m",
        "2. The unit of power is (1) J (2) W (3) N (4) Pa",
        "SECTION B",
        "3. The value of g in m/s^2, to the nearest integer, is ____.",
        "PART B - CHEMISTRY",
        "SECTION A",
        "4. The number of moles in 18 g of water is (1) 1 (2) 2 (3) 0.5 (4) 18",
        filename="jee-main-2024.pdf",
    )
    assert [(e.label, e.question_count) for e in structure.chapters[0].exercises] == [
        ("Part A Physics · Section A", 2),
        ("Part A Physics · Section B", 1),
        ("Part B Chemistry · Section A", 1),
    ]


def test_a_paper_without_sections_starts_after_its_numbered_instructions():
    structure = _paper(
        "Class 9 Science Half-yearly Examination",
        "General Instructions",
        "1. All questions are compulsory.",
        "2. Marks are shown against each question.",
        "1. What is the SI unit of force? [1]",
        "2. State Newton's first law of motion. [2]",
        "3. Explain why a moving bus throws its passengers forward when it stops. [3]",
    )
    assert [(e.label, e.question_count) for e in structure.chapters[0].exercises] == [("Questions", 3)]
    assert _questions(structure)[0] == ("Questions", "1. What is the SI unit of force? [1]")


def test_exercise_titles():
    assert exercise_title("2.3") == "Exercise 2.3"
    assert exercise_title("") == "Exercises"
    assert exercise_title("Section A") == "Section A"
