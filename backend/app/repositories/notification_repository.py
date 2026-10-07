"""Tenant-scoped notification data access."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Notification


class NotificationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(
        self, notification_id: uuid.UUID, org_id: uuid.UUID, user_id: uuid.UUID
    ) -> Notification | None:
        return await self.db.scalar(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.organization_id == org_id,
                Notification.user_id == user_id,
            )
        )

    async def list_for_user(
        self,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        unread_only: bool,
        page: int,
        page_size: int,
    ) -> tuple[list[Notification], int]:
        base = select(Notification).where(
            Notification.organization_id == org_id,
            Notification.user_id == user_id,
        )
        if unread_only:
            base = base.where(Notification.read_at.is_(None))

        total = int(
            await self.db.scalar(
                select(func.count()).select_from(base.subquery())
            )
            or 0
        )

        stmt = (
            base.order_by(Notification.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = list((await self.db.scalars(stmt)).all())
        return rows, total

    async def unread_count(
        self, org_id: uuid.UUID, user_id: uuid.UUID
    ) -> int:
        return int(
            await self.db.scalar(
                select(func.count())
                .select_from(Notification)
                .where(
                    Notification.organization_id == org_id,
                    Notification.user_id == user_id,
                    Notification.read_at.is_(None),
                )
            )
            or 0
        )

    async def mark_read(
        self, notification: Notification
    ) -> Notification:
        if notification.read_at is None:
            notification.read_at = datetime.now(timezone.utc)
            await self.db.flush()
        return notification

    async def mark_all_read(
        self, org_id: uuid.UUID, user_id: uuid.UUID
    ) -> int:
        now = datetime.now(timezone.utc)
        stmt = (
            update(Notification)
            .where(
                Notification.organization_id == org_id,
                Notification.user_id == user_id,
                Notification.read_at.is_(None),
            )
            .values(read_at=now)
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount or 0