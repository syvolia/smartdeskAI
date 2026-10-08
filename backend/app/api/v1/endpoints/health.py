"""Health and readiness endpoints."""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.db.redis import get_redis
from app.db.session import get_db

router = APIRouter(tags=["health"])
logger = get_logger(__name__)


@router.get("/health", summary="Liveness probe")
async def health() -> dict:
    """Return 200 as long as the process is up."""
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
    }


@router.get("/health/ready", summary="Readiness probe")
async def readiness(
    db: AsyncSession = Depends(get_db),
    redis: Redis | None = Depends(get_redis),
) -> JSONResponse:
    """Verify downstream dependencies (Postgres, Redis).

    Logs the underlying error on failure so logs show *why* a check
    failed, not just that it did. This is critical in production where
    the response body is intentionally minimal.
    """
    checks: dict[str, bool] = {"database": False, "redis": False}
    errors: dict[str, str] = {}

    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception as exc:
        errors["database"] = f"{type(exc).__name__}: {exc}"
        logger.error("readiness_db_failed", error=errors["database"])

    if redis is None:
        errors["redis"] = "Redis client not configured"
        logger.error("readiness_redis_not_configured")
    else:
        try:
            await redis.ping()
            checks["redis"] = True
        except Exception as exc:
            errors["redis"] = f"{type(exc).__name__}: {exc}"
            logger.error("readiness_redis_failed", error=errors["redis"])

    ready = all(checks.values())
    body: dict = {
        "status": "ok" if ready else "degraded",
        "checks": checks,
    }
    # In non-production environments, surface the underlying errors so
    # debugging is easier. In production, keep the response minimal and
    # rely on the logs.
    if not ready and not settings.is_production:
        body["errors"] = errors

    return JSONResponse(status_code=200 if ready else 503, content=body)