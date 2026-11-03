"""Uploading files into a book, following their processing, retrying and removing them.

The upload request does only the quick, safe part - receive the file, check it, store it under a
random name, create the `documents` row - and hands the slow reading to the task queue.
"""

import asyncio
import hashlib
import logging
import tempfile
import unicodedata
import uuid
from pathlib import Path, PurePath
from typing import BinaryIO

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.principal import Principal
from app.core.config import get_settings
from app.core.enums import DocumentStatus
from app.core.errors import ConflictError, NotFoundError
from app.core.tasks import TaskQueue
from app.models import Book, Document
from app.rag.ingestion.errors import FileTooLargeError
from app.rag.ingestion.file_checks import CheckedFile, check_file
from app.rag.ingestion.pipeline import process_document
from app.services.library_service import book_visible_to, ensure_can_manage, get_book
from app.storage import FileStorage, new_storage_key

logger = logging.getLogger(__name__)

_COPY_CHUNK = 1024 * 1024


def clean_filename(name: str | None) -> str:
    """Keep only the last part of the name, without control characters. Only ever displayed."""
    base = PurePath((name or "").replace("\\", "/")).name
    base = "".join(ch for ch in unicodedata.normalize("NFC", base) if unicodedata.category(ch)[0] != "C")
    return base.strip()[:255] or "document"


def _receive(source: BinaryIO, target: BinaryIO, max_bytes: int) -> tuple[int, str]:
    """Copy the upload to a private temporary file, hashing it and stopping at the size limit."""
    digest = hashlib.sha256()
    size = 0
    while chunk := source.read(_COPY_CHUNK):
        size += len(chunk)
        if size > max_bytes:
            raise FileTooLargeError(f"This file is larger than {max_bytes // (1024 * 1024)} MB.")
        digest.update(chunk)
        target.write(chunk)
    target.flush()
    return size, digest.hexdigest()


async def upload_document(
    db: AsyncSession,
    principal: Principal,
    book_id: uuid.UUID,
    upload: UploadFile,
    *,
    storage: FileStorage,
    queue: TaskQueue,
) -> Document:
    ensure_can_manage(principal)
    book = await get_book(db, principal, book_id)
    settings = get_settings()

    documents_in_book = await db.scalar(
        select(func.count()).select_from(Document).where(Document.book_id == book.id)
    )
    if (documents_in_book or 0) >= settings.max_documents_per_book:
        raise ConflictError(
            f"A book can have up to {settings.max_documents_per_book} files.", code="document_limit_reached"
        )

    incoming = settings.storage_path / "_incoming"
    incoming.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.NamedTemporaryFile(dir=incoming, prefix="upload-", delete=True) as temporary:
        size, sha256 = await asyncio.to_thread(_receive, upload.file, temporary, settings.max_upload_bytes)
        checked: CheckedFile = await asyncio.to_thread(
            check_file, Path(temporary.name), max_pdf_pages=settings.max_pdf_pages
        )

        duplicate = await db.scalar(
            select(Document.id).where(Document.book_id == book.id, Document.sha256 == sha256)
        )
        if duplicate is not None:
            raise ConflictError("This file is already in this book.", code="document_already_uploaded")

        key = new_storage_key(principal.user.id)
        temporary.seek(0)
        await storage.save(key, temporary)

    document = Document(
        book_id=book.id,
        owner_user_id=principal.user.id,
        original_filename=clean_filename(upload.filename),
        file_kind=checked.kind.value,
        mime_type=checked.mime_type,
        size_bytes=size,
        sha256=sha256,
        storage_key=key,
        page_count=checked.page_count,
        status=DocumentStatus.QUEUED.value,
    )
    db.add(document)
    try:
        await db.commit()
    except IntegrityError:
        # The same file was uploaded twice at the same moment; the other upload won.
        await db.rollback()
        await storage.delete(key)
        raise ConflictError("This file is already in this book.", code="document_already_uploaded") from None

    logger.info("Document %s uploaded to book %s (%s, %d bytes)", document.id, book.id, checked.kind, size)
    await queue.enqueue(process_document, document_id=document.id)
    return document


async def get_document(db: AsyncSession, principal: Principal, document_id: uuid.UUID) -> Document:
    document = await db.scalar(
        select(Document)
        .join(Book, Book.id == Document.book_id)
        .where(Document.id == document_id, book_visible_to(principal))
        .execution_options(populate_existing=True)
    )
    if document is None:
        raise NotFoundError("We couldn't find this document.", code="document_not_found")
    return document


async def retry_document(
    db: AsyncSession, principal: Principal, document_id: uuid.UUID, *, queue: TaskQueue
) -> Document:
    """Read a failed document again, without uploading it again."""
    ensure_can_manage(principal)
    document = await get_document(db, principal, document_id)
    if document.status != DocumentStatus.FAILED:
        raise ConflictError("Only a document that failed can be tried again.", code="document_not_failed")
    document.status = DocumentStatus.QUEUED.value
    document.stage = None
    document.error_code = None
    await db.commit()
    await queue.enqueue(process_document, document_id=document.id)
    return document


async def delete_document(
    db: AsyncSession, principal: Principal, document_id: uuid.UUID, *, storage: FileStorage
) -> None:
    """Remove one file from a book, with every chapter and chunk found in it."""
    ensure_can_manage(principal)
    document = await get_document(db, principal, document_id)
    key = document.storage_key
    await db.delete(document)
    await db.commit()
    try:
        await storage.delete(key)
    except OSError:
        logger.warning("Could not delete the stored file of document %s", document_id, exc_info=True)


async def resume_unfinished_documents(
    session_factory: async_sessionmaker[AsyncSession], queue: TaskQueue
) -> int:
    """At start-up: documents that were waiting or being read when the server stopped are queued again."""
    async with session_factory() as db:
        documents = (
            await db.scalars(
                select(Document).where(
                    Document.status.in_([DocumentStatus.QUEUED.value, DocumentStatus.PROCESSING.value])
                )
            )
        ).all()
        for document in documents:
            document.status = DocumentStatus.QUEUED.value
        await db.commit()
        ids = [document.id for document in documents]
    for document_id in ids:
        await queue.enqueue(process_document, document_id=document_id)
    if ids:
        logger.info("Resumed reading %d unfinished document(s)", len(ids))
    return len(ids)
