"""Background work behind one small interface.

Reading a 300-page book takes minutes, so it never runs inside the upload request. Callers
enqueue a job; the queue runs it later with its own database session.

Today the queue runs jobs inside the API process (`InProcessTaskQueue`). Step 12 swaps in a
Redis-backed worker without changing any caller. Jobs must therefore be safe to run again: the
processing state lives in the database, not in the queue.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from functools import lru_cache
from typing import Any, Protocol

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)

# A job receives its own database session plus keyword arguments (ids only, never objects).
Job = Callable[..., Awaitable[None]]


class TaskQueue(Protocol):
    async def enqueue(self, job: Job, /, **kwargs: Any) -> None: ...


class InProcessTaskQueue:
    """Runs jobs as asyncio tasks in this process, at most `concurrency` at a time.

    If the process stops, running jobs stop with it; unfinished documents and practice sessions
    are picked up again when the API starts (see `app.main.lifespan`).
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession], concurrency: int) -> None:
        self._session_factory = session_factory
        self._semaphore = asyncio.Semaphore(concurrency)
        self._tasks: set[asyncio.Task[None]] = set()

    async def enqueue(self, job: Job, /, **kwargs: Any) -> None:
        task = asyncio.create_task(self._run(job, kwargs), name=f"job:{job.__name__}")
        self._tasks.add(task)  # keep a reference so the task is not garbage-collected
        task.add_done_callback(self._tasks.discard)

    async def _run(self, job: Job, kwargs: dict[str, Any]) -> None:
        async with self._semaphore:
            try:
                async with self._session_factory() as db:
                    await job(db, **kwargs)
            except Exception:
                # The job records its own failure on its rows; this only catches the unexpected.
                logger.exception("Background job %s failed", job.__name__)

    async def wait_idle(self) -> None:
        """Wait until every queued job has finished (used by scripts)."""
        while self._tasks:
            await asyncio.gather(*list(self._tasks), return_exceptions=True)

    async def shutdown(self) -> None:
        for task in list(self._tasks):
            task.cancel()
        await asyncio.gather(*list(self._tasks), return_exceptions=True)


@lru_cache
def get_task_queue() -> InProcessTaskQueue:
    return InProcessTaskQueue(SessionLocal, get_settings().processing_concurrency)
