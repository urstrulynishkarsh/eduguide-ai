"""One uploaded file: its processing progress, retrying, removing."""

import uuid

from fastapi import APIRouter, Response, status

from app.api.deps import CurrentPrincipal, DbSession, Queue, Storage, limit_account
from app.api.v1.library_views import document_out
from app.core.rate_limits import UPLOADS_PER_DAY
from app.schemas.library import DocumentOut
from app.services import document_service

router = APIRouter(prefix="/documents", tags=["My Books"])


@router.get("/{document_id}", response_model=DocumentOut, summary="Processing progress of a file")
async def get_document(document_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession) -> DocumentOut:
    """`progress` is the checklist: each step is `pending`, `active`, `done` or `failed`.
    When `status` is `failed`, `error.message` can be shown to the parent as it is."""
    return document_out(await document_service.get_document(db, principal, document_id))


@router.post(
    "/{document_id}/retry",
    response_model=DocumentOut,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Read a failed file again",
    dependencies=[limit_account(UPLOADS_PER_DAY)],
)
async def retry_document(
    document_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession, queue: Queue
) -> DocumentOut:
    return document_out(await document_service.retry_document(db, principal, document_id, queue=queue))


@router.delete(
    "/{document_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Remove a file from its book"
)
async def delete_document(
    document_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession, storage: Storage
) -> Response:
    await document_service.delete_document(db, principal, document_id, storage=storage)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
