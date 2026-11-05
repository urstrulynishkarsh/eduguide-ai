"""Background work behind one small interface.

Reading a 300-page book takes minutes, so it never runs inside the upload request. Callers enqueue a
job with ids (never objects); the job runs later with its own database session.

Two queues, chosen by REDIS_URL:

* `InProcessTaskQueue` (REDIS_URL empty, the local default): jobs run inside the API process.
  Unfinished work is picked up again when the API starts (`app.main.lifespan`).
* `RedisTaskQueue`: jobs go to Redis and `python -m app.worker` runs them in its own process, so a
  book being read never holds the API up (app/worker.py).

Jobs must be safe to run again: the processing state lives in the database, not in the queue.
"""

import asyncio
import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from functools import lru_cache
from typing import Protocol

import saq
from saq.queue.redis import RedisQueue
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core import metrics
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.redis import get_redis

logger = logging.getLogger(__name__)

# A job receives its own database session plus keyword arguments: ids, or None.
Job = Callable[..., Awaitable[None]]
Ids = dict[str, uuid.UUID | None]

QUEUE_NAME = "eduguide"


class TaskQueue(Protocol):
    async def enqueue(self, job: Job, /, **ids: uuid.UUID | None) -> None: ...

    async def close(self) -> None: ...


def job_key(job: Job, ids: Ids) -> str:
    """`process_document:document_id=…`: one job per piece of work. Refuses anything but ids."""
    for name, value in ids.items():
        if value is not None and not isinstance(value, uuid.UUID):
            raise TypeError(f"{job.__name__}: {name} must be an id, not {type(value).__name__}")
    return job.__name__ + "".join(f":{name}={value}" for name, value in sorted(ids.items()))


async def run_job(session_factory: async_sessionmaker[AsyncSession], job: Job, ids: Ids) -> None:
    """Runs one job in a session of its own and counts it (core/metrics). Raises what the job raises."""
    started = time.perf_counter()
    outcome = "failed"
    try:
        async with session_factory() as db:
            await job(db, **ids)
        outcome = "ok"
    finally:
        metrics.JOBS.labels(job.__name__, outcome).inc()
        metrics.JOB_SECONDS.labels(job.__name__).observe(time.perf_counter() - started)


class InProcessTaskQueue:
    """Runs jobs as asyncio tasks in this process, at most `concurrency` at a time.

    If the process stops, running jobs stop with it; unfinished documents, practice, tests and
    paper analyses are picked up again when the API starts.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession], concurrency: int) -> None:
        self._session_factory = session_factory
        self._semaphore = asyncio.Semaphore(concurrency)
        self._tasks: set[asyncio.Task[None]] = set()

    async def enqueue(self, job: Job, /, **ids: uuid.UUID | None) -> None:
        task = asyncio.create_task(self._run(job, ids), name=f"job:{job.__name__}")
        self._tasks.add(task)  # keep a reference so the task is not garbage-collected
        task.add_done_callback(self._tasks.discard)

    async def _run(self, job: Job, ids: Ids) -> None:
        async with self._semaphore:
            try:
                await run_job(self._session_factory, job, ids)
            except Exception:
                # The job records its own failure on its rows; this only catches the unexpected.
                logger.exception("Background job %s failed", job.__name__)

    async def wait_idle(self) -> None:
        """Wait until every queued job has finished (used by scripts)."""
        while self._tasks:
            await asyncio.gather(*list(self._tasks), return_exceptions=True)

    async def close(self) -> None:
        for task in list(self._tasks):
            task.cancel()
        await asyncio.gather(*list(self._tasks), return_exceptions=True)


# How long a job may run, how often it is tried, and how soon a job of a worker that died is taken
# over: a running job is marked alive every HEARTBEAT_EVERY seconds (app/worker.py); one not marked
# for HEARTBEAT seconds is run again by another worker.
HEARTBEAT = 120
HEARTBEAT_EVERY = 30
JOB_SETTINGS = {
    "timeout": 2 * 60 * 60,
    "heartbeat": HEARTBEAT,
    "retries": 3,
    "retry_delay": 60.0,
    "ttl": 3600,
}


class RedisTaskQueue:
    """Sends jobs to Redis by name, with their ids as text (JSON, never pickle). A job already waiting
    or running for the same ids is not queued a second time."""

    def __init__(self, queue: saq.Queue) -> None:
        self.queue = queue

    async def enqueue(self, job: Job, /, **ids: uuid.UUID | None) -> None:
        text = {name: None if value is None else str(value) for name, value in ids.items()}
        await self.queue.enqueue(
            saq.Job(function=job.__name__, kwargs=text, key=job_key(job, ids), **JOB_SETTINGS)
        )

    async def close(self) -> None:
        await self.queue.disconnect()


def redis_queue() -> saq.Queue:
    return RedisQueue(get_redis(), name=QUEUE_NAME)


@lru_cache
def get_task_queue() -> TaskQueue:
    settings = get_settings()
    if settings.redis_url:
        return RedisTaskQueue(redis_queue())
    return InProcessTaskQueue(SessionLocal, settings.processing_concurrency)
