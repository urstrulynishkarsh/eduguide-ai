"""Search inside books: vectors are stored, filters always hold, labels stay in step."""

import uuid

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DocumentChunk
from app.rag.retrieval import ChunkFilter, search
from tests.api.helpers import API, create_book, register, upload
from tests.fakes import FakeEmbeddings
from tests.samples import NOTES_TEXT, make_pdf


async def _search(db: AsyncSession, text: str, where: ChunkFilter, embedder: FakeEmbeddings):
    return await search(db, query_vector=await embedder.embed_query(text), query_text=text, where=where)


async def test_every_chunk_is_embedded_while_the_book_is_read(
    client: AsyncClient, db_session: AsyncSession, fake_embeddings: FakeEmbeddings
):
    parent = await register(client)
    book = await create_book(client, parent.headers)
    document = (await upload(client, parent.headers, book["id"], make_pdf())).json()

    assert document["progress"][-1] == {"step": "embed_chunks", "state": "done"}
    models = (
        await db_session.scalars(
            select(DocumentChunk.embedding_model).where(DocumentChunk.book_id == book["id"])
        )
    ).all()
    assert models and set(models) == {fake_embeddings.model_name}


async def test_search_finds_by_meaning_and_by_exact_words(
    client: AsyncClient, db_session: AsyncSession, fake_embeddings: FakeEmbeddings
):
    parent = await register(client)
    book = await create_book(client, parent.headers)
    await upload(client, parent.headers, book["id"], make_pdf())
    owner = uuid.UUID(parent.user["id"])

    found = await _search(db_session, "perimeter of a rectangular pool", ChunkFilter(owner), fake_embeddings)
    assert found[0].chunk.meta.get("question_number") == "2"
    assert "pool" in found[0].chunk.content

    # "2.1" is matched as written by the keyword half of the search.
    exercise = await _search(db_session, "Exercise 2.1", ChunkFilter(owner), fake_embeddings)
    assert "Exercise 2.1" in exercise[0].chunk.context_label


async def test_filters_never_let_other_families_classes_or_exercises_in(
    client: AsyncClient, db_session: AsyncSession, fake_embeddings: FakeEmbeddings
):
    parent = await register(client)
    stranger = await register(client)
    maths = await create_book(client, parent.headers)  # class 8
    science = await create_book(
        client, parent.headers, title="Science", subject="Science", class_level="class_5"
    )
    theirs = await create_book(client, stranger.headers)
    for headers, book, data in (
        (parent.headers, maths, make_pdf()),
        (parent.headers, science, NOTES_TEXT.encode()),
        (stranger.headers, theirs, make_pdf(header="Their copy")),
    ):
        await upload(client, headers, book["id"], data, "book.txt" if book is science else "book.pdf")
    owner = uuid.UUID(parent.user["id"])
    chapters = (await client.get(f"{API}/books/{maths['id']}/chapters", headers=parent.headers)).json()
    chapter = (await client.get(f"{API}/chapters/{chapters[1]['id']}", headers=parent.headers)).json()
    exercise_id = uuid.UUID(chapter["exercises"][0]["id"])

    for query in ("solve the equation", "water vapour clouds", "Exercise 2.2 pool", "rational numbers"):
        everything = await _search(db_session, query, ChunkFilter(owner), fake_embeddings)
        assert everything and {p.chunk.owner_user_id for p in everything} == {owner}

        class_8 = await _search(db_session, query, ChunkFilter(owner, class_level="class_8"), fake_embeddings)
        assert {p.chunk.book_id for p in class_8} <= {uuid.UUID(maths["id"])}

        one_exercise = await _search(
            db_session, query, ChunkFilter(owner, exercise_id=exercise_id), fake_embeddings
        )
        assert {p.chunk.exercise_id for p in one_exercise} <= {exercise_id}


async def test_renaming_a_chapter_re_embeds_its_text(
    client: AsyncClient, db_session: AsyncSession, fake_embeddings: FakeEmbeddings
):
    parent = await register(client)
    book = await create_book(client, parent.headers)
    await upload(client, parent.headers, book["id"], make_pdf())
    chapter_id = (await client.get(f"{API}/books/{book['id']}/chapters", headers=parent.headers)).json()[0][
        "id"
    ]
    calls_before = fake_embeddings.calls

    await client.patch(f"{API}/chapters/{chapter_id}", json={"title": "Fractions"}, headers=parent.headers)

    assert fake_embeddings.calls > calls_before
    rows = (
        await db_session.execute(
            select(DocumentChunk.embedding_model, DocumentChunk.embedding).where(
                DocumentChunk.chapter_id == chapter_id
            )
        )
    ).all()
    assert {model for model, _ in rows} == {fake_embeddings.model_name}
    assert all(vector is not None for _, vector in rows)
