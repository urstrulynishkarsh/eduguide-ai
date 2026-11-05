"""The background worker: runs the jobs the API puts in Redis (when REDIS_URL is set).

    python -m app.worker            start it (one or more, on any server that reaches Redis and the database)
    python -m app.worker --check    exit 0 if a worker is alive (the Docker health check)

Only the jobs in JOBS can run: a name that comes from Redis is looked up here, never imported. When it
starts, the worker queues again the work that was left unfinished (as the API does without Redis).
"""

import asyncio
import contextlib
import logging
import sys
import uuid
from typing import Any

from saq import Worker
from saq.worker import async_check_health

from app.adaptive_learning.misconceptions import examine
from app.core import metrics
from app.core.config import get_settings
from app.core.database import SessionLocal, engine
from app.core.logging import configure_logging
from app.core.tasks import HEARTBEAT_EVERY, Job, RedisTaskQueue, TaskQueue, redis_queue, run_job
from app.rag.indexing import embed_stale_chunks
from app.rag.ingestion.pipeline import process_document
from app.services.document_service import resume_unfinished_documents
from app.services.mock_test_service import prepare_test, resume_unfinished_tests
from app.services.paper_analysis_service import analyse_paper, resume_unfinished_analyses
from app.services.practice_service import prepare_session, resume_unfinished_sessions

logger = logging.getLogger(__name__)

JOBS: dict[str, Job] = {
    job.__name__: job
    for job in (process_document, embed_stale_chunks, prepare_session, prepare_test, analyse_paper, examine)
}

# Running jobs that do not finish within this many seconds of a stop are put back in the queue (they
# are safe to run again). An idle worker also takes this long to stop.
_STOP_GRACE_SECONDS = 10


async def resume_unfinished_work(queue: TaskQueue) -> None:
    """Books being read, practice and tests being prepared and papers being analysed when the work
    last stopped are queued again."""
    await resume_unfinished_documents(SessionLocal, queue)
    await resume_unfinished_sessions(SessionLocal, queue)
    await resume_unfinished_tests(SessionLocal, queue)
    await resume_unfinished_analyses(SessionLocal, queue)


async def _beat(saq_job: Any) -> None:
    """Marks a running job alive, so that the job of a worker that died is run again by another."""
    while True:
        await asyncio.sleep(HEARTBEAT_EVERY)
        try:
            await saq_job.update()
        except Exception:
            logger.warning("Could not mark job %s as alive", saq_job.function, exc_info=True)


def _runner(job: Job) -> tuple[str, Any]:
    async def run(ctx: dict[str, Any], **text: str | None) -> None:
        ids = {name: None if value is None else uuid.UUID(value) for name, value in text.items()}
        beat = asyncio.create_task(_beat(ctx["job"]))
        try:
            await run_job(SessionLocal, job, ids)
        finally:
            beat.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await beat  # stopped before the queue records the job as finished

    return job.__name__, run


async def _startup(ctx: dict[str, Any]) -> None:
    metrics.serve(get_settings().metrics_port)
    await resume_unfinished_work(RedisTaskQueue(ctx["worker"].queue))


async def _work(worker: Worker) -> None:
    await worker.queue.connect()
    try:
        await worker.start()
    finally:
        await worker.queue.disconnect()
        await engine.dispose()


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_format)
    if not settings.redis_url:
        sys.exit("REDIS_URL is not set: background jobs run inside the API, so no worker is needed.")
    queue = redis_queue()
    if "--check" in sys.argv[1:]:
        sys.exit(asyncio.run(async_check_health(queue)))
    worker = Worker(
        queue,
        [_runner(job) for job in JOBS.values()],
        concurrency=settings.processing_concurrency,
        startup=_startup,
        shutdown_grace_period_s=_STOP_GRACE_SECONDS,
    )
    asyncio.run(_work(worker))


if __name__ == "__main__":
    main()
