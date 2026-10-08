"""Event bus: local fanout + Redis pub/sub for multi-instance delivery.

Publishing:
  1. Deliver to local connections in this process.
  2. Publish to Redis so other instances can deliver to their connections.

Subscribing:
  1. Subscribe to `realtime:broadcast`.
  2. On message, drop it if it originated on this instance (we already
     delivered locally). Otherwise forward to local connections.

If Redis is unavailable, the bus returns None from the factory and all
publishers no-op. Local WebSocket delivery still works within the single
process (relevant for the Render free tier, where there's only one).
"""

import asyncio
import json
import uuid
from functools import lru_cache

from redis.asyncio import Redis

from app.core.logging import get_logger
from app.db.redis import get_redis
from app.realtime.manager import ConnectionManager, get_connection_manager
from app.realtime.schemas import RealtimeEvent

logger = get_logger(__name__)

BROADCAST_CHANNEL = "realtime:broadcast"


class RealtimeBus:
    def __init__(
        self,
        redis: Redis,
        manager: ConnectionManager,
        *,
        instance_id: str | None = None,
    ) -> None:
        self.redis = redis
        self.manager = manager
        self.instance_id = instance_id or uuid.uuid4().hex
        self._subscriber_task: asyncio.Task[None] | None = None
        self._stopping = False

    # ---------- lifecycle ----------

    async def start(self) -> None:
        if self._subscriber_task is not None:
            return
        self._stopping = False
        self._subscriber_task = asyncio.create_task(self._subscriber_loop())
        logger.info("realtime_bus_started", instance_id=self.instance_id)

    async def stop(self) -> None:
        self._stopping = True
        if self._subscriber_task is not None:
            self._subscriber_task.cancel()
            try:
                await self._subscriber_task
            except (asyncio.CancelledError, Exception):
                pass
            self._subscriber_task = None
        logger.info("realtime_bus_stopped", instance_id=self.instance_id)

    # ---------- publish ----------

    async def publish(self, event: RealtimeEvent) -> None:
        # 1. Local delivery.
        try:
            await self.manager.broadcast(event)
        except Exception:
            logger.exception("realtime_local_broadcast_failed")

        # 2. Redis fanout for other instances.
        try:
            await self.redis.publish(
                BROADCAST_CHANNEL,
                json.dumps(
                    {
                        "instance": self.instance_id,
                        "event": event.to_wire(),
                    }
                ),
            )
        except Exception:
            logger.warning("realtime_publish_failed")

    # ---------- subscribe ----------

    async def _subscriber_loop(self) -> None:
        pubsub = self.redis.pubsub()
        try:
            await pubsub.subscribe(BROADCAST_CHANNEL)
            logger.info("realtime_bus_subscribed", channel=BROADCAST_CHANNEL)
            async for message in pubsub.listen():
                if self._stopping:
                    break
                if message.get("type") != "message":
                    continue
                try:
                    data = json.loads(message["data"])
                except (TypeError, ValueError):
                    continue
                if data.get("instance") == self.instance_id:
                    # We already delivered locally before publishing.
                    continue
                try:
                    event = RealtimeEvent.from_wire(data["event"])
                except Exception:
                    logger.warning("realtime_bad_message")
                    continue
                try:
                    await self.manager.broadcast(event)
                except Exception:
                    logger.exception("realtime_forward_failed")
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("realtime_subscriber_crashed")
        finally:
            try:
                await pubsub.unsubscribe(BROADCAST_CHANNEL)
                await pubsub.aclose()
            except Exception:
                pass


@lru_cache(maxsize=1)
def get_realtime_bus() -> RealtimeBus | None:
    """Process-wide bus. Returns None if Redis is unavailable.

    A bus without Redis still delivers to local connections but won't
    fan out across instances. In single-instance deployments (Render
    free tier), local delivery is all that matters.
    """
    redis = get_redis()
    if redis is None:
        logger.warning("realtime_bus_disabled", reason="no redis client")
        return None
    return RealtimeBus(redis, get_connection_manager())