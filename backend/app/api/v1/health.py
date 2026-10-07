from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.api.deps import get_redis
from app.db.session import get_db
from app.schemas.health import HealthCheck, HealthResponse
from app.services import health as health_service

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def liveness() -> HealthResponse:
    return HealthResponse(status="ok", checks=[HealthCheck(name="api", status="ok")])


@router.get("/health/ready", response_model=HealthResponse)
async def readiness(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> HealthResponse | JSONResponse:
    payload = await health_service.build_readiness(db, redis)
    if payload.status != "ok":
        return JSONResponse(status_code=503, content=payload.model_dump())
    return payload
