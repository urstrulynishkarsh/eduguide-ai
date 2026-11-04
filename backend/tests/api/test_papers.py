"""Previous-year papers: reading a paper into sections and questions, analysing the papers against the
family's textbook, and a test like them. The AI's reading of each paper is scripted."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app import llm
from app.analytics.paper_reading import PaperReading, QuestionReading
from tests.api.helpers import (
    API,
    bank,
    create_book,
    error_code,
    family_with_book,
    start_child_session,
    upload,
)
from tests.fakes import FakeLLM

PAPER_2022 = """CBSE Class X Mathematics
Time Allowed: 3 hours Maximum Marks: 80
SECTION A
1. Which of these is a rational number? (a) pi (b) root 2 (c) 3/4 (d) e
2. The additive inverse of 2/3 is (a) 3/2 (b) -2/3 (c) 2/3 (d) 0
SECTION B
3. Solve 2x + 3 = 7. [2]
"""
PAPER_2023 = """CBSE Class X Mathematics
Time Allowed: 3 hours Maximum Marks: 80
SECTION A
1. Which of these is not a rational number? (a) 1/2 (b) 0.75 (c) root 3 (d) -4
SECTION B
2. Solve 5x - 2 = 3x + 4. [3]
3. The sum of two numbers is 74 and one is 10 more than the other. Find them. [5]
"""


def _reading(year, duration, *questions) -> PaperReading:
    return PaperReading(
        year=year,
        duration_minutes=duration,
        negative_marks=0,
        questions=[QuestionReading(number=n, marks=m, format=f, area=a) for n, m, f, a in questions],
    )


# The sample textbook (tests/samples.py): C1 Rational Numbers (C1.1 Introduction, C1.2 Properties
# of Rational Numbers), C2 Linear Equations in One Variable.
READINGS = (
    # No year on the paper: it comes from the file name.
    _reading(None, None, (1, 1, "mcq", "C1"), (2, 1, "mcq", "C1.2"), (3, 2, "short_answer", "C2")),
    _reading(2023, 180, (1, 1, "mcq", "C1"), (2, 3, "short_answer", "C2"), (3, 5, "long_answer", "C2")),
)


@pytest.fixture
def ai(monkeypatch: pytest.MonkeyPatch):
    def install(fake):
        monkeypatch.setattr(llm, "get_llm_provider", lambda: fake)
        return fake

    return install


async def _papers(client: AsyncClient, parent, child) -> dict:
    book = await create_book(
        client,
        parent.headers,
        title="Maths board papers",
        material_type="previous_year_paper",
        student_id=child["id"],
        class_level=None,
    )
    for name, text in (("maths-2022.txt", PAPER_2022), ("maths-2023.txt", PAPER_2023)):
        response = await upload(client, parent.headers, book["id"], text.encode(), name, "text/plain")
        assert response.json()["status"] == "ready", response.text
    return book


async def test_a_paper_is_read_into_its_sections_and_questions(client: AsyncClient):
    parent, child, _ = await family_with_book(client, "class_10")
    book = await _papers(client, parent, child)

    (paper, _) = (await client.get(f"{API}/books/{book['id']}/chapters", headers=parent.headers)).json()
    assert (paper["label"], paper["exercise_count"], paper["question_count"]) == ("maths 2022", 2, 3)
    detail = (await client.get(f"{API}/chapters/{paper['id']}", headers=parent.headers)).json()
    assert [(e["title"], e["question_count"]) for e in detail["exercises"]] == [
        ("Section A", 2),
        ("Section B", 1),
    ]


async def test_analysing_papers_shows_where_the_marks_go_and_a_test_like_them(
    client: AsyncClient, db_session: AsyncSession, ai, task_queue
):
    parent, child, chapter = await family_with_book(client, "class_10")
    book = await _papers(client, parent, child)
    url = f"{API}/books/{book['id']}/paper-analysis"
    assert (await client.get(url, headers=parent.headers)).json()["status"] == "none"
    fake = ai(FakeLLM(*READINGS))

    started = await client.post(url, headers=parent.headers)

    assert started.status_code == 202, started.text
    assert task_queue.jobs.count("analyse_paper") == 2
    # The AI chooses from the textbook's chapters and topics, never the paper book's own.
    listed = fake.requests[0]["messages"][0].content
    assert (
        "C1.2 1.2 Properties of Rational Numbers" in listed
        and "maths 2022" not in listed.split("<chapters>")[1]
    )
    analysis = (await client.get(url, headers=parent.headers)).json()
    assert analysis["status"] == "ready"
    assert [(p["title"], p["year"], p["questions"], p["total_marks"]) for p in analysis["papers"]] == [
        ("maths 2023", 2023, 3, 9),
        ("maths 2022", 2022, 3, 4),
    ]
    linear, rational = analysis["chapters"]
    assert (linear["chapter"], linear["marks_per_paper"], linear["share"], linear["papers"]) == (
        "Chapter 2 Linear Equations in One Variable",
        5.0,
        0.769,
        2,
    )
    assert [(y["year"], y["marks"]) for y in linear["by_year"]] == [(2022, 2), (2023, 8)]
    assert linear["trend"] is None  # three dated papers are needed
    assert linear["practice"]["chapter_id"] == chapter["id"]
    assert (rational["questions"], rational["marks_per_paper"]) == (3, 1.5)
    assert [(t["topic"], t["questions"]) for t in analysis["topics"]] == [
        ("1.2 Properties of Rational Numbers", 1)
    ]
    assert [(f["format"], f["questions"]) for f in analysis["formats"]] == [
        ("mcq", 3),
        ("short_answer", 2),
        ("long_answer", 1),
    ]
    # The latest paper's layout.
    assert analysis["layout_year"] == 2023
    assert [(s["title"], s["questions"], s["marks"], s["formats"]) for s in analysis["layout"]] == [
        ("Section A", 1, 1, ["mcq"]),
        ("Section B", 2, 3, ["short_answer", "long_answer"]),
    ]

    # A test like them: the latest paper's layout, from the chapter with the most marks.
    await bank(db_session, parent, child, chapter, count=1)
    await bank(db_session, parent, child, chapter, count=1, fmt="short_answer")
    await bank(db_session, parent, child, chapter, count=1, fmt="long_answer")
    created = await client.post(
        f"{API}/mock-tests", json={**analysis["test"], "student_id": child["id"]}, headers=parent.headers
    )
    assert created.status_code == 201, created.text
    test = created.json()
    assert (test["kind"], test["status"], test["book_title"]) == (
        "previous_year",
        "ready",
        "Maths board papers",
    )
    assert [(s["code"], s["title"], s["marks"], len(s["questions"])) for s in test["sections"]] == [
        ("A", "Objective questions", 1, 1),
        ("B", "Short answer questions", 3, 2),
    ]
    # Its pace is the paper's: 180 minutes for 9 marks, so 7 marks take 140 minutes.
    assert (test["total_marks"], test["duration_minutes"]) == (7, 140)


async def test_who_may_analyse_and_what(client: AsyncClient, ai):
    parent, child, _ = await family_with_book(client, "class_10")
    book = await _papers(client, parent, child)
    url = f"{API}/books/{book['id']}/paper-analysis"

    off = await client.post(url, headers=parent.headers)
    assert (off.status_code, error_code(off)) == (503, "ai_not_configured")
    child_mode = await client.post(url, headers=await start_child_session(client, parent, child["id"]))
    assert (child_mode.status_code, error_code(child_mode)) == (403, "parent_required")
    (textbook,) = [
        b
        for b in (await client.get(f"{API}/books", headers=parent.headers)).json()["items"]
        if b["id"] != book["id"]
    ]
    not_papers = await client.post(f"{API}/books/{textbook['id']}/paper-analysis", headers=parent.headers)
    assert (not_papers.status_code, error_code(not_papers)) == (422, "not_a_paper_book")
    young = await create_book(
        client, parent.headers, material_type="previous_year_paper", class_level="class_8"
    )
    too_young = await client.post(f"{API}/books/{young['id']}/paper-analysis", headers=parent.headers)
    assert (too_young.status_code, error_code(too_young)) == (422, "not_for_class")
    empty = await create_book(
        client, parent.headers, material_type="previous_year_paper", class_level="class_10"
    )
    ai(FakeLLM())
    nothing = await client.post(f"{API}/books/{empty['id']}/paper-analysis", headers=parent.headers)
    assert (nothing.status_code, error_code(nothing)) == (422, "no_papers")

    # A test like the papers needs them analysed first.
    unanalysed = await client.post(
        f"{API}/mock-tests",
        json={"student_id": child["id"], "kind": "previous_year", "book_id": book["id"]},
        headers=parent.headers,
    )
    assert (unanalysed.status_code, error_code(unanalysed)) == (422, "paper_not_analysed")
    other = await client.get(
        f"{API}/books/{book['id']}/paper-analysis", headers=(await family_with_book(client))[0].headers
    )
    assert other.status_code == 404
