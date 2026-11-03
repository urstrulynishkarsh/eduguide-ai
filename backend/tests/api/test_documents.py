"""Uploading files into a book and following how they are read."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.library_views import progress
from app.core.config import get_settings
from app.models import Document, DocumentChunk
from app.rag.ingestion import pipeline
from app.storage import get_file_storage
from tests.api.helpers import API, create_book, error_code, register, upload
from tests.conftest import InlineTaskQueue
from tests.fakes import FakeOCR
from tests.samples import HINDI_TEXT, NOTES_TEXT, make_docx, make_pdf, make_scanned_pdf

_ALL_STEPS = [
    "extract_text",
    "detect_chapters",
    "detect_exercises",
    "detect_topics",
    "make_chunks",
    "embed_chunks",
]


async def test_upload_a_textbook_pdf_and_find_its_chapters(client: AsyncClient, task_queue: InlineTaskQueue):
    parent = await register(client)
    book = await create_book(client, parent.headers)

    response = await upload(client, parent.headers, book["id"], make_pdf(), filename="Class 8 Maths.pdf")

    assert response.status_code == 202
    document = response.json()
    assert task_queue.jobs == ["process_document"]
    assert document["original_filename"] == "Class 8 Maths.pdf"
    assert document["file_type"] == "pdf"
    assert document["page_count"] == 4
    assert document["status"] == "ready"
    assert document["error"] is None
    assert [step["step"] for step in document["progress"]] == _ALL_STEPS
    assert {step["state"] for step in document["progress"]} == {"done"}
    summary = document["summary"]
    assert (summary["chapters"], summary["topics"], summary["exercises"], summary["questions"]) == (
        2,
        4,
        3,
        9,
    )
    assert summary["examples"] == 2

    book_now = (await client.get(f"{API}/books/{book['id']}", headers=parent.headers)).json()
    assert book_now["status"] == "ready"
    assert book_now["chapter_count"] == 2

    chapters = (await client.get(f"{API}/books/{book['id']}/chapters", headers=parent.headers)).json()
    assert [(c["number"], c["label"], c["page_start"], c["page_end"]) for c in chapters] == [
        (1, "Chapter 1 Rational Numbers", 1, 2),
        (2, "Chapter 2 Linear Equations in One Variable", 3, 4),
    ]
    assert [(c["topic_count"], c["exercise_count"], c["question_count"]) for c in chapters] == [
        (2, 1, 3),
        (2, 2, 6),
    ]


async def test_chapter_page_and_exercise_questions_with_sources(client: AsyncClient):
    parent = await register(client)
    book = await create_book(client, parent.headers)
    await upload(client, parent.headers, book["id"], make_pdf())
    chapters = (await client.get(f"{API}/books/{book['id']}/chapters", headers=parent.headers)).json()

    chapter = (await client.get(f"{API}/chapters/{chapters[1]['id']}", headers=parent.headers)).json()

    assert [(t["number"], t["title"]) for t in chapter["topics"]] == [
        ("2.1", "Introduction"),
        ("2.2", "Solving Equations"),
    ]
    assert [(e["label"], e["title"], e["question_count"]) for e in chapter["exercises"]] == [
        ("2.1", "Exercise 2.1", 4),
        ("2.2", "Exercise 2.2", 2),
    ]
    assert chapter["example_count"] == 1
    assert chapter["has_summary"] is False

    exercise = (
        await client.get(f"{API}/exercises/{chapter['exercises'][0]['id']}", headers=parent.headers)
    ).json()
    assert [q["number"] for q in exercise["questions"]] == ["1", "2", "3", "4"]
    first = exercise["questions"][0]
    assert first["text"] == "Solve the following equations.\n1. x - 2 = 7"
    assert first["instructions"] == "Solve the following equations."
    assert first["origin"] == "textbook"
    assert first["source"] == {
        "book_id": book["id"],
        "book_title": "Class 8 Mathematics",
        "chapter": "Chapter 2 Linear Equations in One Variable",
        "exercise": "2.1",
        "page": 4,
    }


async def test_chunks_carry_the_metadata_search_will_filter_on(client: AsyncClient, db_session: AsyncSession):
    parent = await register(client)
    book = await create_book(client, parent.headers, board="cbse")
    await upload(client, parent.headers, book["id"], make_pdf())

    chunks = (
        await db_session.scalars(
            select(DocumentChunk).where(DocumentChunk.book_id == book["id"]).order_by(DocumentChunk.position)
        )
    ).all()

    assert {chunk.owner_user_id.hex for chunk in chunks} == {parent.user["id"].replace("-", "")}
    assert {(chunk.class_level, chunk.board, chunk.subject, chunk.language) for chunk in chunks} == {
        ("class_8", "cbse", "Mathematics", "en")
    }
    question = next(c for c in chunks if c.meta.get("question_number") == "3" and c.page_start == 4)
    assert question.content_type == "exercise_question"
    assert question.exercise_id is not None and question.chapter_id is not None
    assert question.context_label == (
        "Class 8 · Mathematics · Chapter 2 Linear Equations in One Variable · 2.2 Solving Equations · "
        "Exercise 2.1 · Question 3"
    )
    assert [chunk.position for chunk in chunks] == list(range(len(chunks)))
    # Running headers and page numbers were removed from the text.
    assert not any("Mathematics" in chunk.content.splitlines()[0] for chunk in chunks)


async def test_word_and_text_files(client: AsyncClient, db_session: AsyncSession):
    parent = await register(client)
    science = await create_book(
        client, parent.headers, title="Science notes", subject="Science", material_type="notes"
    )
    hindi = await create_book(client, parent.headers, title="Ganit", language="hi")

    docx = await upload(
        client,
        parent.headers,
        science["id"],
        make_docx(),
        filename="notes.docx",
        content_type="application/octet-stream",  # browsers sometimes send this; the content decides
    )
    notes = await upload(
        client, parent.headers, science["id"], NOTES_TEXT.encode(), "water.txt", "text/plain"
    )
    hindi_doc = await upload(
        client, parent.headers, hindi["id"], HINDI_TEXT.encode(), "bhinn.txt", "text/plain"
    )

    assert [r.json()["file_type"] for r in (docx, notes, hindi_doc)] == ["docx", "txt", "txt"]
    assert {r.json()["status"] for r in (docx, notes, hindi_doc)} == {"ready"}

    chapters = (await client.get(f"{API}/books/{science['id']}/chapters", headers=parent.headers)).json()
    assert [c["label"] for c in chapters] == ["Chapter 3 Plants and Animals", "Chapter 5 The Water Cycle"]

    languages = set(
        (
            await db_session.scalars(
                select(DocumentChunk.language).where(DocumentChunk.book_id == hindi["id"])
            )
        ).all()
    )
    assert languages == {"hi"}


async def test_unsupported_files_are_refused_with_a_clear_message(client: AsyncClient):
    parent = await register(client)
    book = await create_book(client, parent.headers)

    photo = await upload(
        client, parent.headers, book["id"], b"\x89PNG\r\n\x1a\n" + b"\x00" * 50, "page.png", "image/png"
    )
    assert photo.status_code == 415
    assert error_code(photo) == "unsupported_file_type"
    assert "PDF" in photo.json()["error"]["message"]

    fake_pdf = await upload(client, parent.headers, book["id"], b"\x00\x01binary" * 20, "book.pdf")
    assert fake_pdf.status_code == 415

    empty = await upload(client, parent.headers, book["id"], b"", "empty.txt", "text/plain")
    assert empty.status_code == 422
    assert error_code(empty) == "empty_file"

    assert (await client.get(f"{API}/books/{book['id']}", headers=parent.headers)).json()["documents"] == []


async def test_the_same_file_twice_in_one_book_is_refused(client: AsyncClient):
    parent = await register(client)
    book = await create_book(client, parent.headers)
    other_book = await create_book(client, parent.headers, title="Copy")
    data = make_pdf()
    assert (await upload(client, parent.headers, book["id"], data)).status_code == 202

    again = await upload(client, parent.headers, book["id"], data, filename="renamed.pdf")

    assert again.status_code == 409
    assert error_code(again) == "document_already_uploaded"
    assert (await upload(client, parent.headers, other_book["id"], data)).status_code == 202


async def test_files_over_the_size_limit_are_refused(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(get_settings(), "max_upload_mb", 1)
    parent = await register(client)
    book = await create_book(client, parent.headers)

    response = await upload(
        client, parent.headers, book["id"], b"a" * (1024 * 1024 + 100 * 1024), "big.txt", "text/plain"
    )

    assert response.status_code == 413
    assert error_code(response) == "file_too_large"
    assert "1 MB" in response.json()["error"]["message"]


async def test_large_json_bodies_are_refused(client: AsyncClient):
    parent = await register(client)
    response = await client.post(
        f"{API}/books", json={"title": "x" * (2 * 1024 * 1024), "subject": "Maths"}, headers=parent.headers
    )
    assert response.status_code == 413
    assert error_code(response) == "payload_too_large"


async def test_scanned_book_without_ocr_fails_with_a_parent_friendly_message(client: AsyncClient):
    parent = await register(client)
    book = await create_book(client, parent.headers)

    document = (await upload(client, parent.headers, book["id"], make_scanned_pdf(), "scan.pdf")).json()

    assert document["status"] == "failed"
    assert document["error"]["code"] == "scanned_document"
    assert "scanned" in document["error"]["message"]
    assert [step["state"] for step in document["progress"]] == ["failed"] + ["pending"] * 5
    assert (await client.get(f"{API}/books/{book['id']}", headers=parent.headers)).json()[
        "status"
    ] == "failed"


async def test_a_failed_document_can_be_read_again_once_ocr_is_available(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    parent = await register(client)
    book = await create_book(
        client, parent.headers, title="EVS", subject="Environmental Studies", class_level="class_4"
    )
    failed = (await upload(client, parent.headers, book["id"], make_scanned_pdf(), "scan.pdf")).json()
    assert failed["status"] == "failed"

    ocr = FakeOCR()
    monkeypatch.setattr(pipeline, "get_ocr_provider", lambda: ocr)
    response = await client.post(f"{API}/documents/{failed['id']}/retry", headers=parent.headers)

    assert response.status_code == 202
    document = response.json()
    assert document["status"] == "ready"
    assert document["summary"]["ocr_pages"] == 2
    assert document["summary"]["chapters"] == 1
    chapters = (await client.get(f"{API}/books/{book['id']}/chapters", headers=parent.headers)).json()
    assert chapters[0]["label"] == "Chapter 6 Our Environment"

    again = await client.post(f"{API}/documents/{failed['id']}/retry", headers=parent.headers)
    assert again.status_code == 409
    assert error_code(again) == "document_not_failed"


async def test_a_missing_stored_file_is_reported(client: AsyncClient, db_session: AsyncSession):
    parent = await register(client)
    book = await create_book(client, parent.headers)
    document = (await upload(client, parent.headers, book["id"], make_pdf())).json()
    key = await db_session.scalar(select(Document.storage_key).where(Document.id == document["id"]))
    await get_file_storage().delete(key)
    row = await db_session.get(Document, document["id"])
    row.status = "failed"
    await db_session.commit()

    retried = (await client.post(f"{API}/documents/{document['id']}/retry", headers=parent.headers)).json()

    assert retried["status"] == "failed"
    assert retried["error"]["code"] == "file_missing"


async def test_progress_while_a_document_is_being_read(client: AsyncClient, db_session: AsyncSession):
    parent = await register(client)
    book = await create_book(client, parent.headers)
    document = (await upload(client, parent.headers, book["id"], make_pdf())).json()
    row = await db_session.get(Document, document["id"])

    row.status, row.stage = "processing", "detect_exercises"
    assert [step.state for step in progress(row)] == [
        "done",
        "done",
        "active",
        "pending",
        "pending",
        "pending",
    ]
    row.status, row.stage = "queued", None
    assert {step.state for step in progress(row)} == {"pending"}


async def test_removing_one_file_keeps_the_rest_of_the_book(client: AsyncClient):
    parent = await register(client)
    book = await create_book(client, parent.headers)
    first = (await upload(client, parent.headers, book["id"], make_pdf())).json()
    await upload(client, parent.headers, book["id"], NOTES_TEXT.encode(), "water.txt", "text/plain")

    response = await client.delete(f"{API}/documents/{first['id']}", headers=parent.headers)

    assert response.status_code == 204
    chapters = (await client.get(f"{API}/books/{book['id']}/chapters", headers=parent.headers)).json()
    assert [c["label"] for c in chapters] == ["Chapter 5 The Water Cycle"]


async def test_parent_renames_a_chapter(client: AsyncClient, db_session: AsyncSession):
    parent = await register(client)
    book = await create_book(client, parent.headers)
    await upload(client, parent.headers, book["id"], make_pdf())
    chapter_id = (await client.get(f"{API}/books/{book['id']}/chapters", headers=parent.headers)).json()[0][
        "id"
    ]

    response = await client.patch(
        f"{API}/chapters/{chapter_id}", json={"title": "Rational Numbers (revised)"}, headers=parent.headers
    )

    assert response.status_code == 200
    assert response.json()["label"] == "Chapter 1 Rational Numbers (revised)"
    labels = (
        await db_session.scalars(
            select(DocumentChunk.context_label).where(DocumentChunk.chapter_id == chapter_id)
        )
    ).all()
    assert labels and all("Chapter 1 Rational Numbers (revised)" in label for label in labels)

    blank = await client.patch(f"{API}/chapters/{chapter_id}", json={"title": " "}, headers=parent.headers)
    assert blank.status_code == 422


async def test_upload_options_are_published(client: AsyncClient):
    options = (await client.get(f"{API}/meta/options")).json()
    assert [item["code"] for item in options["material_types"]][:2] == ["textbook", "notes"]
    assert options["upload"]["accepted_extensions"] == [".pdf", ".docx", ".txt"]
    assert options["upload"]["max_file_mb"] == 50
