"""Build a NotificationService bound to the current request's db + Redis."""

from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.redis import get_redis
from app.db.session import get_db
from app.notifications.channels.in_app import InAppChannel
from app.notifications.service import NotificationService


def get_notification_service(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> NotificationService:
    """Request-scoped notification service with all channels registered.

    To add an email or WebSocket channel later, append it here and
    everything downstream keeps working.
    """
    channels = [InAppChannel(db=db, redis=redis)]
    return NotificationService(db=db, redis=redis, channels=channels)