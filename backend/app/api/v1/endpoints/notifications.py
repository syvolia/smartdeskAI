"""Notification endpoints."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.db.redis import get_redis
from app.db.session import get_db
from app.models import User, UserRole
from app.core.exceptions import ForbiddenError, NotFoundError
from app.notifications.factory import get_notification_service
from app.notifications.service import NotificationService
from app.notifications.sla_scanner import SLANotificationScanner
from app.repositories.notification_repository import NotificationRepository
from app.schemas.notification import (
    MarkAllReadResponse,
    MarkReadResponse,
    NotificationListResponse,
    NotificationResponse,
    UnreadCountResponse,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])

UNREAD_CACHE_KEY = "notif:unread:{org_id}:{user_id}"


def _unread_key(org_id, user_id) -> str:
    return UNREAD_CACHE_KEY.format(org_id=org_id, user_id=user_id)


async def _invalidate_unread(redis, org_id, user_id) -> None:
    try:
        await redis.delete(_unread_key(org_id, user_id))
    except Exception:
        pass


@router.get(
    "",
    response_model=NotificationListResponse,
    summary="List notifications for the current user.",
)
async def list_notifications(
    unread_only: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationListResponse:
    repo = NotificationRepository(db)
    rows, total = await repo.list_for_user(
        user.organization_id,
        user.id,
        unread_only=unread_only,
        page=page,
        page_size=page_size,
    )
    unread = await repo.unread_count(user.organization_id, user.id)
    pages = (total + page_size - 1) // page_size if page_size else 0
    return NotificationListResponse(
        items=[NotificationResponse.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
        unread_count=unread,
    )


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
    summary="Fast unread count (Redis-cached).",
)
async def unread_count(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis),
) -> UnreadCountResponse:
    key = _unread_key(user.organization_id, user.id)
    try:
        cached = await redis.get(key)
        if cached is not None:
            return UnreadCountResponse(unread_count=int(cached))
    except Exception:
        pass

    repo = NotificationRepository(db)
    count = await repo.unread_count(user.organization_id, user.id)
    try:
        await redis.set(key, count, ex=300)
    except Exception:
        pass
    return UnreadCountResponse(unread_count=count)


@router.patch(
    "/{notification_id}/read",
    response_model=MarkReadResponse,
    summary="Mark a notification as read.",
)
async def mark_read(
    notification_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis),
) -> MarkReadResponse:
    repo = NotificationRepository(db)
    n = await repo.get(notification_id, user.organization_id, user.id)
    if n is None:
        raise NotFoundError("Notification not found.")
    await repo.mark_read(n)
    await db.commit()
    await _invalidate_unread(redis, user.organization_id, user.id)
    return MarkReadResponse(notification=NotificationResponse.model_validate(n))


@router.patch(
    "/read-all",
    response_model=MarkAllReadResponse,
    summary="Mark every notification as read.",
)
async def mark_all_read(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis),
) -> MarkAllReadResponse:
    repo = NotificationRepository(db)
    updated = await repo.mark_all_read(user.organization_id, user.id)
    await db.commit()
    await _invalidate_unread(redis, user.organization_id, user.id)
    return MarkAllReadResponse(updated=updated, unread_count=0)


@router.post(
    "/sla-scan",
    summary="Run the SLA warning/breach scan (admin only).",
)
async def sla_scan(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    notifications: NotificationService = Depends(get_notification_service),
) -> dict:
    if user.role != UserRole.ADMIN:
        raise ForbiddenError("Only administrators can run the SLA scan.")
    scanner = SLANotificationScanner(db=db, notifications=notifications)
    result = await scanner.scan(user.organization_id)
    await db.commit()
    return result