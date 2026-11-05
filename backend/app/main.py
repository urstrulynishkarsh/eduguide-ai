"""The FastAPI application. Start it with:  uvicorn app.main:app --reload"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api import health
from app.api.v1.router import api_v1_router
from app.core import metrics
from app.core.config import get_settings
from app.core.database import engine
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import BodySizeLimitMiddleware, RequestContextMiddleware
from app.core.tasks import InProcessTaskQueue, get_task_queue
from app.worker import resume_unfinished_work

logger = logging.getLogger(__name__)

_DESCRIPTION = """
Backend of **EduGuide AI** - a personal tutor, practice generator, study planner
and parent assistant for Indian students from Nursery to Class 12.

**Trying the API here:** call `POST /api/v1/auth/login`, copy the `access_token`,
press **Authorize** and paste it.
"""


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    metrics.serve(get_settings().metrics_port)
    queue = get_task_queue()
    if isinstance(queue, InProcessTaskQueue):
        # The jobs run in this process: the work left unfinished when it last stopped is picked up
        # again. (With Redis, the worker does this.)
        try:
            await resume_unfinished_work(queue)
        except Exception:
            logger.warning("Could not resume unfinished work (is the database running?)", exc_info=True)
    yield
    await queue.close()
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_format)

    # No API docs in production: the API is only for the Next.js server.
    docs = {"docs_url": None, "redoc_url": None, "openapi_url": None} if settings.is_production else {}
    app = FastAPI(
        title=settings.app_name, version=__version__, description=_DESCRIPTION, lifespan=lifespan, **docs
    )

    # Middleware added last runs first: request id -> CORS -> body size limit -> the app.
    app.add_middleware(BodySizeLimitMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )
    app.add_middleware(RequestContextMiddleware)
    register_exception_handlers(app)

    app.include_router(health.router)
    app.include_router(api_v1_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
