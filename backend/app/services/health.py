from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.schemas.health import HealthCheck, HealthResponse


async def check_postgres(db: AsyncSession) -> HealthCheck:
    try:
        await db.execute(text("SELECT 1"))
        return HealthCheck(name="postgres", status="ok")
    except Exception as exc:  # noqa: BLE001
        return HealthCheck(name="postgres", status="error", detail=str(exc))


async def check_redis(redis: Redis) -> HealthCheck:
    try:
        pong = await redis.ping()
        if not pong:
            return HealthCheck(name="redis", status="error", detail="PING returned false")
        return HealthCheck(name="redis", status="ok")
    except Exception as exc:  # noqa: BLE001
        return HealthCheck(name="redis", status="error", detail=str(exc))


async def build_readiness(db: AsyncSession, redis: Redis) -> HealthResponse:
    checks = [await check_postgres(db), await check_redis(redis)]
    status = "ok" if all(check.status == "ok" for check in checks) else "degraded"
    return HealthResponse(status=status, checks=checks)
