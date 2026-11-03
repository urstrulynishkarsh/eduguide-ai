"""The FastAPI application. Start it with:  uvicorn app.main:app --reload"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api import health
from app.api.v1.router import api_v1_router
from app.core.config import get_settings
from app.core.database import SessionLocal, engine
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import BodySizeLimitMiddleware, RequestContextMiddleware
from app.core.tasks import get_task_queue
from app.services.document_service import resume_unfinished_documents
from app.services.practice_service import resume_unfinished_sessions

logger = logging.getLogger(__name__)

_DESCRIPTION = """
Backend of **EduGuide AI** - a personal tutor, practice generator, study planner
and parent assistant for Indian students from Nursery to Class 12.

**Trying the API here:** call `POST /api/v1/auth/login`, copy the `access_token`,
press **Authorize** and paste it.
"""


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    queue = get_task_queue()
    try:
        # Books being read, and practice being prepared, when the server last stopped are picked up again.
        await resume_unfinished_documents(SessionLocal, queue)
        await resume_unfinished_sessions(SessionLocal, queue)
    except Exception:
        logger.warning("Could not resume unfinished work (is the database running?)", exc_info=True)
    yield
    await queue.shutdown()
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(title=settings.app_name, version=__version__, description=_DESCRIPTION, lifespan=lifespan)

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
