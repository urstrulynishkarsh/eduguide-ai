"""Small helpers that keep the API tests readable."""

import uuid
from dataclasses import dataclass
from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Question
from tests.samples import NOTES_TEXT, make_pdf

API = "/api/v1"
PASSWORD = "Str0ng-Passw0rd"


@dataclass
class Account:
    user: dict[str, Any]
    tokens: dict[str, Any]
    email: str
    password: str

    @property
    def headers(self) -> dict[str, str]:
        return bearer(self.tokens["access_token"])


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def register(client: AsyncClient, role: str = "parent", **overrides: Any) -> Account:
    payload = {
        "role": role,
        "full_name": "Test User",
        "email": f"user-{uuid.uuid4().hex[:12]}@example.com",
        "password": PASSWORD,
        **overrides,
    }
    response = await client.post(f"{API}/auth/register", json=payload)
    assert response.status_code == 201, response.text
    body = response.json()
    return Account(
        user=body["user"], tokens=body["tokens"], email=payload["email"], password=payload["password"]
    )


def child_payload(**profile_overrides: Any) -> dict[str, Any]:
    """Aarav, Class 7, CBSE - the example child from the product spec."""
    return {
        "name": "Aarav",
        "age": 12,
        "profile": {
            "class_level": "class_7",
            "board": "cbse",
            "medium": "en",
            "primary_language": "hinglish",
            "subjects": ["Mathematics", "Science"],
            **profile_overrides,
        },
    }


async def add_child(client: AsyncClient, parent: Account, **profile_overrides: Any) -> dict[str, Any]:
    response = await client.post(
        f"{API}/students", json=child_payload(**profile_overrides), headers=parent.headers
    )
    assert response.status_code == 201, response.text
    return response.json()


async def start_child_session(client: AsyncClient, parent: Account, student_id: str) -> dict[str, str]:
    """Returns the headers of a child-mode session."""
    response = await client.post(f"{API}/students/{student_id}/session", headers=parent.headers)
    assert response.status_code == 200, response.text
    return bearer(response.json()["access_token"])


def error_code(response: Any) -> str:
    return response.json()["error"]["code"]


def book_payload(**overrides: Any) -> dict[str, Any]:
    return {"title": "Class 8 Mathematics", "subject": "Mathematics", "class_level": "class_8", **overrides}


async def create_book(client: AsyncClient, headers: dict[str, str], **overrides: Any) -> dict[str, Any]:
    response = await client.post(f"{API}/books", json=book_payload(**overrides), headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


async def upload(
    client: AsyncClient,
    headers: dict[str, str],
    book_id: str,
    data: bytes,
    filename: str = "book.pdf",
    content_type: str = "application/pdf",
) -> Any:
    return await client.post(
        f"{API}/books/{book_id}/documents",
        files={"file": (filename, data, content_type)},
        headers=headers,
    )


async def family_with_book(client: AsyncClient, class_level: str = "class_7") -> tuple[Account, dict, dict]:
    """A parent, a child of the class, and the child's book (the sample maths book; a short text for
    UKG). Returns the last chapter, with its topics and exercises."""
    parent = await register(client)
    child = await add_child(client, parent, class_level=class_level)
    book = await create_book(client, parent.headers, student_id=child["id"], class_level=None)
    if class_level == "ukg":
        await upload(client, parent.headers, book["id"], NOTES_TEXT.encode(), "water.txt", "text/plain")
    else:
        await upload(client, parent.headers, book["id"], make_pdf())
    chapters = (await client.get(f"{API}/books/{book['id']}/chapters", headers=parent.headers)).json()
    chapter = (await client.get(f"{API}/chapters/{chapters[-1]['id']}", headers=parent.headers)).json()
    return parent, child, chapter


# What is shown and the right answer, by format: option 0, the number 1, or a written answer.
_BANK_FORMATS: dict[str, tuple[dict, dict]] = {
    "mcq": ({"options": ["right", "wrong", "no"]}, {"option": 0}),
    "numerical": ({"unit": "cm"}, {"value": 1}),
    "short_answer": ({}, {"model_answer": "Both sides stay equal.", "key_points": ["equal", "both sides"]}),
    "long_answer": ({}, {"model_answer": "A long answer.", "key_points": ["one", "two", "three", "four"]}),
}


async def bank(
    db: AsyncSession,
    parent: Account,
    child: dict,
    chapter: dict,
    *,
    count: int,
    fmt: str = "mcq",
    difficulty: str = "medium",
) -> None:
    """Checked questions in the family's question bank for the chapter's last topic (the chapter
    itself when it has none), as if written earlier - so practice and tests need no AI."""
    body, answer = _BANK_FORMATS[fmt]
    topics = chapter["topics"]
    db.add_all(
        Question(
            owner_user_id=uuid.UUID(parent.user["id"]),
            book_id=uuid.UUID(chapter["book_id"]),
            chapter_id=uuid.UUID(chapter["id"]),
            topic_id=uuid.UUID(topics[-1]["id"]) if topics else None,
            origin="generated",
            class_level=child["profile"]["class_level"],
            subject="Mathematics",
            format=fmt,
            style="recall",
            difficulty=difficulty,
            language=child["profile"]["primary_language"],
            body={"text": f"Question {uuid.uuid4().hex[:6]}", **body},
            answer=answer,
            hints=["A nudge."],
            solution={"concept": "The idea.", "steps": ["A step."], "final_answer": "right"},
            source_chunk_ids=[],
            validation={"checked_by": "test"},
        )
        for _ in range(count)
    )
    await db.commit()
