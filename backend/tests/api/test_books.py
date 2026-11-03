"""My Books: creating books, listing them, changing and deleting them, and who may see what."""

from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import Document, DocumentChunk
from tests.api.helpers import (
    API,
    add_child,
    book_payload,
    create_book,
    error_code,
    register,
    start_child_session,
    upload,
)
from tests.samples import make_pdf


async def test_parent_creates_a_book(client: AsyncClient):
    parent = await register(client)

    response = await client.post(f"{API}/books", json=book_payload(), headers=parent.headers)

    assert response.status_code == 201
    book = response.json()
    assert book["title"] == "Class 8 Mathematics"
    assert book["class_level"] == "class_8"
    assert book["class_label"] == "Class 8"
    assert book["board"] == "other"  # nothing given and no child chosen
    assert book["language"] == "en"
    assert book["material_type"] == "textbook"
    assert book["status"] == "empty"
    assert book["chapter_count"] == 0
    assert book["documents"] == []


async def test_book_for_a_child_takes_class_board_and_language_from_the_child(client: AsyncClient):
    parent = await register(client)
    child = await add_child(client, parent, class_level="class_7", board="cbse", medium="hi")

    book = await create_book(
        client,
        parent.headers,
        title="Ganit",
        subject="Mathematics",
        class_level=None,
        student_id=child["id"],
        material_type="previous_year_paper",
    )

    assert (book["class_level"], book["board"], book["language"]) == ("class_7", "cbse", "hi")
    assert book["student_id"] == child["id"]
    assert book["material_type"] == "previous_year_paper"


async def test_class_is_required_when_no_child_is_chosen(client: AsyncClient):
    parent = await register(client)
    response = await client.post(f"{API}/books", json=book_payload(class_level=None), headers=parent.headers)
    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["field"] == "class_level"


async def test_book_fields_are_validated(client: AsyncClient):
    parent = await register(client)
    for bad in ({"title": "  "}, {"material_type": "comic"}, {"language": "xx"}, {"class_level": "class_13"}):
        response = await client.post(f"{API}/books", json=book_payload(**bad), headers=parent.headers)
        assert response.status_code == 422, bad


async def test_library_is_newest_first_with_pages(client: AsyncClient):
    parent = await register(client)
    ids = [(await create_book(client, parent.headers, title=f"Book {n}"))["id"] for n in range(5)]

    first = (await client.get(f"{API}/books", params={"limit": 2}, headers=parent.headers)).json()
    assert [book["id"] for book in first["items"]] == [ids[4], ids[3]]
    assert first["next_cursor"]

    second = (
        await client.get(
            f"{API}/books", params={"limit": 2, "cursor": first["next_cursor"]}, headers=parent.headers
        )
    ).json()
    assert [book["id"] for book in second["items"]] == [ids[2], ids[1]]

    last = (
        await client.get(
            f"{API}/books", params={"limit": 2, "cursor": second["next_cursor"]}, headers=parent.headers
        )
    ).json()
    assert [book["id"] for book in last["items"]] == [ids[0]]
    assert last["next_cursor"] is None

    broken = await client.get(f"{API}/books", params={"cursor": "not-a-cursor"}, headers=parent.headers)
    assert broken.status_code == 422
    assert error_code(broken) == "invalid_cursor"


async def test_changing_the_subject_updates_the_labels_of_the_book_text(
    client: AsyncClient, db_session: AsyncSession
):
    parent = await register(client)
    book = await create_book(client, parent.headers)
    assert (await upload(client, parent.headers, book["id"], make_pdf())).json()["status"] == "ready"

    response = await client.patch(
        f"{API}/books/{book['id']}",
        json={"subject": "Maths", "class_level": "class_7"},
        headers=parent.headers,
    )

    assert response.status_code == 200
    assert (response.json()["subject"], response.json()["class_level"]) == ("Maths", "class_7")
    chunks = (
        await db_session.scalars(select(DocumentChunk).where(DocumentChunk.book_id == book["id"]))
    ).all()
    assert chunks
    assert {(chunk.subject, chunk.class_level) for chunk in chunks} == {("Maths", "class_7")}
    assert all(chunk.context_label.startswith("Class 7 · Maths · ") for chunk in chunks)

    cleared = await client.patch(f"{API}/books/{book['id']}", json={"title": None}, headers=parent.headers)
    assert cleared.status_code == 422


async def test_deleting_a_book_removes_its_files(client: AsyncClient, db_session: AsyncSession):
    parent = await register(client)
    book = await create_book(client, parent.headers)
    document = (await upload(client, parent.headers, book["id"], make_pdf())).json()
    key = await db_session.scalar(select(Document.storage_key).where(Document.id == document["id"]))
    stored_file = get_settings().storage_path / key
    assert stored_file.is_file()

    response = await client.delete(f"{API}/books/{book['id']}", headers=parent.headers)

    assert response.status_code == 204
    assert (await client.get(f"{API}/books/{book['id']}", headers=parent.headers)).status_code == 404
    assert (await client.get(f"{API}/documents/{document['id']}", headers=parent.headers)).status_code == 404
    assert not stored_file.exists()
    assert await db_session.scalar(select(func.count()).select_from(DocumentChunk)) == 0


async def test_other_families_cannot_see_or_touch_a_book(client: AsyncClient):
    owner = await register(client)
    stranger = await register(client)
    book = await create_book(client, owner.headers)
    document = (await upload(client, owner.headers, book["id"], make_pdf())).json()
    chapters = (await client.get(f"{API}/books/{book['id']}/chapters", headers=owner.headers)).json()
    chapter = (await client.get(f"{API}/chapters/{chapters[0]['id']}", headers=owner.headers)).json()
    exercise_id = chapter["exercises"][0]["id"]

    not_found = [
        await client.get(f"{API}/books/{book['id']}", headers=stranger.headers),
        await client.patch(f"{API}/books/{book['id']}", json={"title": "Mine"}, headers=stranger.headers),
        await client.delete(f"{API}/books/{book['id']}", headers=stranger.headers),
        await upload(client, stranger.headers, book["id"], make_pdf(header="Other")),
        await client.get(f"{API}/books/{book['id']}/chapters", headers=stranger.headers),
        await client.get(f"{API}/documents/{document['id']}", headers=stranger.headers),
        await client.post(f"{API}/documents/{document['id']}/retry", headers=stranger.headers),
        await client.delete(f"{API}/documents/{document['id']}", headers=stranger.headers),
        await client.get(f"{API}/chapters/{chapter['id']}", headers=stranger.headers),
        await client.patch(f"{API}/chapters/{chapter['id']}", json={"title": "x"}, headers=stranger.headers),
        await client.get(f"{API}/exercises/{exercise_id}", headers=stranger.headers),
    ]
    assert [response.status_code for response in not_found] == [404] * len(not_found)
    assert (await client.get(f"{API}/books", headers=stranger.headers)).json()["items"] == []

    # A book cannot be made for another family's child either.
    other_child = await add_child(client, owner)
    response = await client.post(
        f"{API}/books", json=book_payload(student_id=other_child["id"]), headers=stranger.headers
    )
    assert response.status_code == 404
    assert error_code(response) == "student_not_found"

    # And nothing changed for the owner.
    assert (await client.get(f"{API}/books/{book['id']}", headers=owner.headers)).json()["title"] == book[
        "title"
    ]


async def test_child_mode_reads_family_books_but_cannot_change_them(client: AsyncClient):
    parent = await register(client)
    aarav = await add_child(client, parent)
    anaya = await add_child(client, parent, class_level="ukg")
    family = await create_book(client, parent.headers, title="Family dictionary")
    for_aarav = await create_book(client, parent.headers, title="Aarav maths", student_id=aarav["id"])
    for_anaya = await create_book(client, parent.headers, title="Anaya rhymes", student_id=anaya["id"])
    aarav_session = await start_child_session(client, parent, aarav["id"])

    listed = (await client.get(f"{API}/books", headers=aarav_session)).json()["items"]
    assert {book["id"] for book in listed} == {family["id"], for_aarav["id"]}
    assert (await client.get(f"{API}/books/{for_anaya['id']}", headers=aarav_session)).status_code == 404

    refused = [
        await client.post(f"{API}/books", json=book_payload(), headers=aarav_session),
        await client.patch(f"{API}/books/{family['id']}", json={"title": "Mine"}, headers=aarav_session),
        await client.delete(f"{API}/books/{family['id']}", headers=aarav_session),
        await upload(client, aarav_session, family["id"], make_pdf()),
    ]
    assert [response.status_code for response in refused] == [403] * 4
    assert {error_code(response) for response in refused} == {"parent_required"}


async def test_parent_filters_the_library_by_child(client: AsyncClient):
    parent = await register(client)
    aarav = await add_child(client, parent)
    anaya = await add_child(client, parent, class_level="ukg")
    family = await create_book(client, parent.headers, title="Family")
    await create_book(client, parent.headers, title="Anaya", student_id=anaya["id"])
    for_aarav = await create_book(client, parent.headers, title="Aarav", student_id=aarav["id"])

    listed = (
        await client.get(f"{API}/books", params={"student_id": aarav["id"]}, headers=parent.headers)
    ).json()
    assert [book["id"] for book in listed["items"]] == [for_aarav["id"], family["id"]]


async def test_student_with_own_login_manages_their_own_books(client: AsyncClient):
    student = await register(client, role="student")
    me = (await client.get(f"{API}/auth/me", headers=student.headers)).json()
    await client.put(
        f"{API}/students/{me['active_student']['id']}/profile",
        json={"class_level": "class_12", "board": "cbse", "stream": "science", "goal": "jee"},
        headers=student.headers,
    )

    book = await create_book(
        client, student.headers, title="Physics Part 1", subject="Physics", class_level=None
    )

    assert book["student_id"] == me["active_student"]["id"]
    assert book["class_level"] == "class_12"
    assert (await client.delete(f"{API}/books/{book['id']}", headers=student.headers)).status_code == 204


async def test_removing_a_child_keeps_the_family_book(client: AsyncClient):
    parent = await register(client)
    child = await add_child(client, parent)
    book = await create_book(client, parent.headers, student_id=child["id"])

    await client.delete(f"{API}/students/{child['id']}", headers=parent.headers)

    kept = await client.get(f"{API}/books/{book['id']}", headers=parent.headers)
    assert kept.status_code == 200
    assert kept.json()["student_id"] is None
