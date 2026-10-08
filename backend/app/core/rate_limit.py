"""Redis-backed sliding-window rate limiter.

Two failure modes:
- If Redis is unavailable or misconfigured, requests are allowed. Losing
  auth is worse than losing rate limiting for a brief window.
- Keys are namespaced per route + identity (user id or client IP).

Usage:

    @router.post("/login", dependencies=[Depends(rate_limit("auth:login", 10, 60))])
    async def login(...): ...
"""

import time
import uuid
from collections.abc import Callable

from fastapi import Depends, Request
from redis.exceptions import RedisError

from app.core.exceptions import RateLimitedError
from app.core.logging import get_logger
from app.db.redis import get_redis

logger = get_logger(__name__)


def _identity(request: Request) -> str:
    """User id from Authorization header if present, else client IP."""
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        # Hash the token so we don't store the raw value as a Redis key.
        import hashlib

        token = auth.split(" ", 1)[1].strip()
        return "tok:" + hashlib.sha256(token.encode()).hexdigest()[:24]

    # Trust X-Forwarded-For only if behind a proxy. For local dev this is
    # the direct client IP.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return "ip:" + forwarded.split(",")[0].strip()
    if request.client is not None:
        return "ip:" + request.client.host
    return "ip:unknown"


def rate_limit(
    scope: str,
    limit: int,
    window_seconds: int,
) -> Callable:
    """Build a FastAPI dependency enforcing `limit` calls per window.

    Uses a sorted set per identity, trimmed to `window_seconds`. This is
    a true sliding window — no burst allowance at window boundaries.

    Fails open: if Redis is None or unreachable, requests are allowed.
    """

    async def _check(
        request: Request,
        redis=Depends(get_redis),
    ) -> None:
        if redis is None:
            return  # fail open — never block requests when Redis is down

        key = f"rl:{scope}:{_identity(request)}"
        now_ms = int(time.time() * 1000)
        cutoff_ms = now_ms - window_seconds * 1000
        member = f"{now_ms}:{uuid.uuid4().hex[:8]}"

        try:
            pipe = redis.pipeline()
            pipe.zremrangebyscore(key, 0, cutoff_ms)
            pipe.zadd(key, {member: now_ms})
            pipe.zcard(key)
            pipe.expire(key, window_seconds + 5)
            _, _, count, _ = await pipe.execute()
        except RedisError:
            logger.warning("rate_limit_redis_error", scope=scope)
            return

        if int(count) > limit:
            # Undo the increment so a rejected call doesn't extend the ban.
            try:
                await redis.zrem(key, member)
            except RedisError:
                pass
            logger.info(
                "rate_limit_exceeded",
                scope=scope,
                identity=_identity(request),
                limit=limit,
            )
            raise RateLimitedError(
                "Too many requests. Please slow down.",
                details={"retry_after_seconds": window_seconds},
            )

    return _check