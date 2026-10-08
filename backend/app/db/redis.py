"""Async Redis client accessor.

If Redis is unreachable or misconfigured, the client returns None and
callers degrade gracefully — the app still serves requests. Rate limiting
fails open, notification dedupe is skipped, and realtime pub/sub is a
no-op. None of those are critical for basic operation.
"""

from redis.asyncio import Redis, from_url

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_redis: Redis | None = None


def _is_valid_redis_url(url: str) -> bool:
    return url.startswith(("redis://", "rediss://", "unix://"))


def get_redis() -> Redis | None:
    """Return a process-wide Redis client, or None if misconfigured."""
    global _redis
    if _redis is not None:
        return _redis

    url = settings.redis_url
    if not _is_valid_redis_url(url):
        logger.error(
            "redis_url_invalid",
            reason="scheme must be redis://, rediss://, or unix://",
            scheme=url.split("://", 1)[0] if "://" in url else "none",
        )
        return None

    try:
        _redis = from_url(url, encoding="utf-8", decode_responses=True)
    except Exception as exc:
        logger.error("redis_client_creation_failed", error=str(exc))
        return None

    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        try:
            await _redis.aclose()
        except Exception:
            pass
        _redis = None