"""Jobs through Redis: queued once per piece of work, ids only, run by the worker (Step 12)."""

import asyncio
import uuid

import pytest
from redis.asyncio import Redis
from saq import Worker
from saq.queue.redis import RedisQueue

from app import worker as worker_module
from app.core.tasks import RedisTaskQueue, job_key
from app.rag.ingestion.pipeline import process_document


def _queues(redis: Redis) -> tuple[RedisQueue, RedisTaskQueue]:
    saq_queue = RedisQueue(redis, name="test")
    return saq_queue, RedisTaskQueue(saq_queue)


async def _work(saq_queue: RedisQueue, *jobs) -> None:
    """Runs what is queued, then stops."""
    await Worker(
        saq_queue, [worker_module._runner(job) for job in jobs], burst=True, dequeue_timeout=1
    ).start()


async def test_the_same_work_is_queued_once(redis: Redis):
    saq_queue, queue = _queues(redis)
    document_id = uuid.uuid4()
    await queue.enqueue(process_document, document_id=document_id)
    await queue.enqueue(process_document, document_id=document_id)  # already waiting
    await queue.enqueue(process_document, document_id=uuid.uuid4())
    assert await saq_queue.count("queued") == 2


async def test_only_ids_go_to_redis(redis: Redis):
    _, queue = _queues(redis)
    with pytest.raises(TypeError, match="must be an id"):
        await queue.enqueue(process_document, document_id="../../etc/passwd")


async def test_the_worker_runs_a_job_with_its_ids(redis: Redis):
    seen = []

    async def remember(db, *, book_id: uuid.UUID, topic_id: uuid.UUID | None) -> None:
        seen.append((book_id, topic_id))

    saq_queue, queue = _queues(redis)
    book_id = uuid.uuid4()
    await queue.enqueue(remember, book_id=book_id, topic_id=None)
    await _work(saq_queue, remember)
    assert seen == [(book_id, None)]
    # Done: the same work may be queued again.
    await queue.enqueue(remember, book_id=book_id, topic_id=None)
    assert await saq_queue.count("incomplete") == 1


async def test_a_running_job_is_marked_alive(redis: Redis, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(worker_module, "HEARTBEAT_EVERY", 0.05)
    saq_queue, queue = _queues(redis)
    marks = []

    async def slow(db, *, book_id: uuid.UUID) -> None:
        for _ in range(3):
            await asyncio.sleep(0.1)
            job = await saq_queue.job(job_key(slow, {"book_id": book_id}))
            marks.append(job.touched)

    await queue.enqueue(slow, book_id=uuid.uuid4())
    await _work(saq_queue, slow)
    assert len(set(marks)) == 3  # touched again while it ran


def test_the_worker_knows_every_job_by_its_name():
    assert all(name == job.__name__ for name, job in worker_module.JOBS.items())
    assert len(worker_module.JOBS) == 6
