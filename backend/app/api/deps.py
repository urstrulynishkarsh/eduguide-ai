"""Dependencies shared by the routes."""

from typing import Annotated, Any

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentPrincipal, ParentPrincipal
from app.core import rate_limits
from app.core.database import get_db
from app.core.rate_limits import Limit
from app.core.tasks import TaskQueue, get_task_queue
from app.storage import FileStorage, get_file_storage

DbSession = Annotated[AsyncSession, Depends(get_db)]
Storage = Annotated[FileStorage, Depends(get_file_storage)]
Queue = Annotated[TaskQueue, Depends(get_task_queue)]
RateCounter = Annotated[rate_limits.Counter, Depends(rate_limits.get_counter)]


def client_address(request: Request) -> str:
    """The browser's address: uvicorn takes it from X-Forwarded-For when the Next.js server (a trusted
    proxy, FORWARDED_ALLOW_IPS) sends it."""
    return request.client.host if request.client else "unknown"


def limit_address(*limits: Limit) -> Any:
    """For a route's `dependencies`: each request counts against the caller's address."""

    async def count(request: Request, counter: RateCounter) -> None:
        for limit in limits:
            await rate_limits.check(counter, limit, client_address(request))

    return Depends(count)


def limit_account(*limits: Limit) -> Any:
    """For a route's `dependencies`: each request counts against the family's account (in child mode,
    the parent's)."""

    async def count(principal: CurrentPrincipal, counter: RateCounter) -> None:
        for limit in limits:
            await rate_limits.check(counter, limit, principal.user.id.hex)

    return Depends(count)


__all__ = [
    "CurrentPrincipal",
    "DbSession",
    "ParentPrincipal",
    "Queue",
    "RateCounter",
    "Storage",
    "client_address",
    "limit_account",
    "limit_address",
]
