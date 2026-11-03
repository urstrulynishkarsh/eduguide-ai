"""Cursor pages for lists that grow (docs/03 §3.9): newest first, `?limit=&cursor=`.

The cursor is the (created_at, id) of the last row of the page, so a row added meanwhile never
shifts the next page.
"""

import base64
import binascii
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInputError


def _encode(created_at: datetime, row_id: uuid.UUID) -> str:
    raw = f"{created_at.isoformat()}|{row_id}".encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _decode(cursor: str) -> tuple[datetime, uuid.UUID]:
    try:
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)).decode()
        created, row_id = raw.split("|")
        return datetime.fromisoformat(created), uuid.UUID(row_id)
    except (ValueError, binascii.Error, UnicodeDecodeError):
        raise InvalidInputError(
            "This page link is not valid.",
            code="invalid_cursor",
            details=[{"field": "cursor", "message": "Invalid cursor."}],
        ) from None


async def newest_first(
    db: AsyncSession, query: Select[Any], model: Any, *, limit: int, cursor: str | None
) -> tuple[list[Any], str | None]:
    """One page of `query` (rows of `model`, which has `created_at` and `id`) and the next cursor."""
    if cursor:
        created, row_id = _decode(cursor)
        query = query.where(tuple_(model.created_at, model.id) < tuple_(created, row_id))
    rows = list(
        (await db.scalars(query.order_by(model.created_at.desc(), model.id.desc()).limit(limit + 1))).all()
    )
    next_cursor = _encode(rows[limit - 1].created_at, rows[limit - 1].id) if len(rows) > limit else None
    return rows[:limit], next_cursor
