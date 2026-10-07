"""Async Redis client accessor."""

from redis.asyncio import Redis, from_url

from app.core.config import settings

_redis: Redis | None = None


def get_redis() -> Redis:
    """Return a process-wide Redis client (created lazily)."""
    global _redis
    if _redis is None:
        _redis = from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis


async def close_redis() -> None:
    """Close the shared Redis client on shutdown."""
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None