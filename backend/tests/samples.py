"""Small sample books made on the fly for tests: PDF (with and without bookmarks), DOCX, TXT and
a "scanned" PDF that has only a picture of a page. The text is written for these tests."""

import io

from docx import Document as new_docx
from PIL import Image, ImageDraw
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

PAGE_WIDTH, PAGE_HEIGHT = A4
LEFT = 60
TOP = PAGE_HEIGHT - 60
LINE = 16

Line = tuple[str, str]  # (style, text) - style: "chapter", "title", "heading", "body"

_STYLES = {
    "chapter": ("Helvetica", 13),
    "title": ("Helvetica-Bold", 22),
    "heading": ("Helvetica-Bold", 14),
    "body": ("Helvetica", 11),
}

# Two chapters in the style of a Class 8 mathematics textbook.
MATHS_BOOK: list[list[Line]] = [
    [
        ("chapter", "Chapter 1"),
        ("title", "Rational Numbers"),
        ("heading", "1.1 Introduction"),
        ("body", "In mathematics we often begin with natural numbers. When we put zero with them"),
        ("body", "we get whole numbers. Rational numbers are numbers of the form p/q where q is"),
        ("body", "not zero. In this chapter we study how to add, subtract and compare them."),
        ("heading", "1.2 Properties of Rational Numbers"),
        ("body", "Rational numbers are closed under addition, subtraction and multiplication."),
        ("body", "Example 1: Find the sum of 3/7 and 2/7."),
        ("body", "Solution: Both fractions have the same denominator, so we add the numerators."),
        ("body", "3/7 + 2/7 = 5/7."),
    ],
    [
        ("heading", "EXERCISE 1.1"),
        ("body", "Find the value of each of the following."),
        ("body", "1. 2/3 + 4/3"),
        ("body", "2. 5/8 - 3/8"),
        ("body", "(i) Write your answer in the lowest terms."),
        ("body", "3. Is 0 a rational number? Give a reason."),
        ("heading", "What have we discussed?"),
        ("body", "Rational numbers are closed under addition and multiplication."),
    ],
    [
        ("chapter", "Chapter 2"),
        ("title", "Linear Equations in One Variable"),
        ("heading", "2.1 Introduction"),
        ("body", "An equation is a statement that two expressions are equal. In a linear"),
        ("body", "equation the highest power of the variable is one, for example 2x + 4 = 10."),
        ("heading", "2.2 Solving Equations"),
        ("body", "To solve an equation we do the same operation on both sides."),
        ("body", "Example 2: Solve 2x + 4 = 10."),
        ("body", "Solution: Subtract 4 from both sides to get 2x = 6. Divide by 2, so x = 3."),
    ],
    [
        ("heading", "EXERCISE 2.1"),
        ("body", "Solve the following equations."),
        ("body", "1. x - 2 = 7"),
        ("body", "2. y + 3 = 10"),
        ("body", "3. 6 = z + 2"),
        ("body", "4. 3x = 12"),
        ("heading", "EXERCISE 2.2"),
        ("body", "1. If you subtract 1/2 from a number and multiply the result by 1/2, you get 1/8."),
        ("body", "What is the number?"),
        ("body", "2. The perimeter of a rectangular pool is 154 m. Its length is 2 m more than"),
        ("body", "twice its breadth. What are the length and the breadth of the pool?"),
    ],
]


def make_pdf(
    pages: list[list[Line]] = MATHS_BOOK,
    *,
    header: str | None = "Mathematics",
    outline: list[tuple[str, int]] | None = None,
) -> bytes:
    """A text PDF. `header` is printed at the top of every page with the page number at the bottom,
    like a real textbook. `outline` adds bookmarks: (title, 0-based page index)."""
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    for index, lines in enumerate(pages):
        if outline:
            for number, (title, page_index) in enumerate(outline):
                if page_index == index:
                    pdf.bookmarkPage(f"b{number}")
                    pdf.addOutlineEntry(title, f"b{number}", level=0)
        y = TOP
        if header:
            pdf.setFont("Helvetica", 9)
            pdf.drawString(LEFT, PAGE_HEIGHT - 30, header)
        for style, text in lines:
            font, size = _STYLES[style]
            pdf.setFont(font, size)
            y -= max(LINE, size + 6)
            pdf.drawString(LEFT, y, text)
        pdf.setFont("Helvetica", 9)
        pdf.drawString(PAGE_WIDTH / 2, 30, str(index + 1))
        pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def make_scanned_pdf(pages: int = 2) -> bytes:
    """Pages that contain only an image - like a scanned book. There is no text to extract."""
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    for _ in range(pages):
        image = Image.new("L", (600, 800), color=255)
        drawing = ImageDraw.Draw(image)
        for row in range(10):
            drawing.rectangle([50, 60 + row * 60, 550, 80 + row * 60], fill=0)
        pdf.drawInlineImage(image, 40, 40, width=PAGE_WIDTH - 80, height=PAGE_HEIGHT - 80)
        pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def make_docx() -> bytes:
    """School notes in Word, with heading styles and a table."""
    document = new_docx()
    document.add_heading("Science Notes", level=0)
    document.add_heading("Chapter 3 Plants and Animals", level=1)
    document.add_heading("3.1 Parts of a Plant", level=2)
    document.add_paragraph("A plant has roots, a stem and leaves. Roots take water from the soil.")
    document.add_paragraph("Leaves make food for the plant using sunlight.")
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Part"
    table.cell(0, 1).text = "Job"
    table.cell(1, 0).text = "Root"
    table.cell(1, 1).text = "Takes in water"
    document.add_heading("Exercises", level=2)
    document.add_paragraph("1. Name the parts of a plant.")
    document.add_paragraph("2. Which part of the plant makes food?")
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


HINDI_TEXT = """अध्याय 4
भिन्न

4.1 भिन्न क्या है
जब किसी पूरी चीज़ को बराबर भागों में बाँटते हैं तो हर भाग एक भिन्न कहलाता है।

उदाहरण 1: एक रोटी के चार बराबर भाग किए गए। एक भाग कितना है?
हल: एक भाग 1/4 है।

प्रश्नावली 4.1
1. 1/2 और 1/4 में कौन बड़ा है?
2. 3/4 को चित्र बनाकर दिखाइए।
"""

NOTES_TEXT = """# Chapter 5 The Water Cycle

## 5.1 Evaporation
The sun heats water in rivers and seas. The water turns into vapour and rises.

## 5.2 Condensation
High in the sky the vapour cools and forms tiny drops. Many drops together make clouds.

Example 1: Why do we see drops on a cold glass of water?
Solution: Water vapour in the air cools on the glass and becomes drops.

## Exercises
1. What is evaporation?
2. How are clouds formed?
"""
