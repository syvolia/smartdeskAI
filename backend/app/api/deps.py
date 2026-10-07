from fastapi import Request
from redis.asyncio import Redis

from app.db.redis import get_redis as get_shared_redis


async def get_redis(request: Request) -> Redis:
    redis = getattr(request.app.state, "redis", None)
    if redis is not None:
        return redis
    return get_shared_redis()
