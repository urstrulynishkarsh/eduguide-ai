"""My Books: the library, and uploading files into a book."""

import uuid
from typing import Annotated

from fastapi import APIRouter, File, Query, Response, UploadFile, status

from app.api.deps import CurrentPrincipal, DbSession, Queue, Storage
from app.api.v1.library_views import book_out, chapter_out, document_out
from app.models import Book
from app.schemas.common import ErrorResponse
from app.schemas.library import BookCreate, BookOut, BookPage, BookUpdate, ChapterOut, DocumentOut
from app.services import document_service, library_service

router = APIRouter(prefix="/books", tags=["My Books"])


async def _book_response(db: DbSession, book: Book) -> BookOut:
    counts = await library_service.chapter_counts(db, [book.id])
    return book_out(book, counts.get(book.id, 0))


@router.post("", response_model=BookOut, status_code=status.HTTP_201_CREATED, summary="Add a book")
async def create_book(data: BookCreate, principal: CurrentPrincipal, db: DbSession) -> BookOut:
    """Creates an empty book; files are added with `POST /books/{id}/documents`.

    Leave out class, board and language to take them from the child given in `student_id`."""
    book = await library_service.create_book(db, principal, data)
    return book_out(book, 0)


@router.get("", response_model=BookPage, summary="My Learning Library")
async def list_books(
    principal: CurrentPrincipal,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query(max_length=200)] = None,
    student_id: Annotated[
        uuid.UUID | None, Query(description="Only books for this child (and family books).")
    ] = None,
) -> BookPage:
    """Newest first. In child mode: the family's shared books and the child's own."""
    books, next_cursor = await library_service.list_books(
        db, principal, limit=limit, cursor=cursor, student_id=student_id
    )
    counts = await library_service.chapter_counts(db, [book.id for book in books])
    return BookPage(items=[book_out(book, counts.get(book.id, 0)) for book in books], next_cursor=next_cursor)


@router.get("/{book_id}", response_model=BookOut, summary="One book, with the progress of its files")
async def get_book(book_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession) -> BookOut:
    return await _book_response(db, await library_service.get_book(db, principal, book_id))


@router.patch("/{book_id}", response_model=BookOut, summary="Change a book's details")
async def update_book(
    book_id: uuid.UUID, data: BookUpdate, principal: CurrentPrincipal, db: DbSession, queue: Queue
) -> BookOut:
    return await _book_response(
        db, await library_service.update_book(db, principal, book_id, data, queue=queue)
    )


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a book")
async def delete_book(
    book_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession, storage: Storage
) -> Response:
    """Deletes the book with all its files and everything found in them."""
    await library_service.delete_book(db, principal, book_id, storage)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{book_id}/documents",
    response_model=DocumentOut,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload a file into a book",
    responses={
        409: {"model": ErrorResponse, "description": "The file is already in this book, or the book is full"},
        413: {"model": ErrorResponse, "description": "The file is too large"},
        415: {"model": ErrorResponse, "description": "Not a PDF, DOCX or TXT file"},
    },
)
async def upload_document(
    book_id: uuid.UUID,
    file: Annotated[UploadFile, File(description="A PDF, Word (.docx) or text (.txt) file.")],
    principal: CurrentPrincipal,
    db: DbSession,
    storage: Storage,
    queue: Queue,
) -> DocumentOut:
    """Answers at once with `status: "queued"`; the book is read in the background.
    Poll `GET /documents/{id}` to follow the progress checklist."""
    document = await document_service.upload_document(
        db, principal, book_id, file, storage=storage, queue=queue
    )
    return document_out(document)


@router.get("/{book_id}/chapters", response_model=list[ChapterOut], summary="Chapters of a book")
async def list_chapters(book_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession) -> list[ChapterOut]:
    chapters = await library_service.list_chapters(db, principal, book_id)
    counts = await library_service.chapter_details(db, [chapter.id for chapter in chapters])
    return [chapter_out(chapter, counts[chapter.id]) for chapter in chapters]
