"""Health checks for monitoring and deployment."""

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app import __version__
from app.api.deps import DbSession
from app.core.config import get_settings
from app.core.redis import get_redis

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Is the API process running?")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@router.get("/health/ready", summary="Can the API reach its database (and Redis, when it is used)?")
async def ready(db: DbSession) -> JSONResponse:
    checks: dict[str, str] = {}
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "up"
    except Exception:
        logger.exception("Readiness check failed: database is not reachable")
        checks["database"] = "down"
    if get_settings().redis_url:
        try:
            await get_redis().ping()
            checks["redis"] = "up"
        except Exception:
            logger.exception("Readiness check failed: Redis is not reachable")
            checks["redis"] = "down"
    if "down" in checks.values():
        return JSONResponse(status_code=503, content={"status": "unavailable", **checks})
    return JSONResponse(content={"status": "ready", **checks})
