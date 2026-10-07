"""In-app channel: writes Notification rows and updates Redis caches."""

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models import Notification
from app.notifications.base import NotificationMessage

logger = get_logger(__name__)

UNREAD_KEY = "notif:unread:{org_id}:{user_id}"
PUBSUB_CHANNEL = "notif:events:{org_id}"


def _unread_key(org_id, user_id) -> str:
    return UNREAD_KEY.format(org_id=org_id, user_id=user_id)


class InAppChannel:
    name = "in_app"

    def __init__(self, db: AsyncSession, redis: Redis) -> None:
        self.db = db
        self.redis = redis

    async def deliver(self, message: NotificationMessage) -> None:
        row = Notification(
            organization_id=message.organization_id,
            user_id=message.user_id,
            type=message.type,
            title=message.title,
            body=message.body,
            entity_type=message.entity_type,
            entity_id=message.entity_id,
        )
        self.db.add(row)
        await self.db.flush()

        # Bump the cached unread counter. If the cache doesn't have the key
        # (cold start, eviction), leave it absent — the next GET recomputes.
        key = _unread_key(message.organization_id, message.user_id)
        try:
            await self.redis.incr(key)
        except Exception:
            logger.warning("unread_cache_incr_failed", key=key)

        # Publish for future WebSocket subscribers. No-op if nobody listens.
        try:
            await self.redis.publish(
                PUBSUB_CHANNEL.format(org_id=message.organization_id),
                str(row.id),
            )
        except Exception:
            logger.warning("notification_publish_failed")

        logger.info(
            "notification_delivered",
            channel=self.name,
            type=message.type.value,
            user_id=str(message.user_id),
            org_id=str(message.organization_id),
            entity_type=message.entity_type,
            entity_id=str(message.entity_id) if message.entity_id else None,
        )