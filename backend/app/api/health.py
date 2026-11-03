"""Health checks for monitoring and deployment."""

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app import __version__
from app.api.deps import DbSession

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Is the API process running?")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@router.get("/health/ready", summary="Can the API reach its database?")
async def ready(db: DbSession) -> JSONResponse:
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Readiness check failed: database is not reachable")
        return JSONResponse(status_code=503, content={"status": "unavailable", "database": "down"})
    return JSONResponse(content={"status": "ready", "database": "up"})
