"""Notification preferences.

Every authenticated user can read and update their own. Admins can also
read and update another user's in the same org.
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.core.exceptions import ForbiddenError, NotFoundError
from app.db.session import get_db
from app.models import NotificationPreference, User, UserRole
from app.schemas.admin import (
    ChannelPreference,
    NotificationPreferencesResponse,
    NotificationPreferencesUpdateRequest,
)

router = APIRouter(prefix="/notification-preferences", tags=["admin"])

DEFAULT_CHANNEL = ChannelPreference(email=True, in_app=True)


async def _load_or_create(
    db: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID
) -> NotificationPreference:
    pref = await db.scalar(
        select(NotificationPreference).where(NotificationPreference.user_id == user_id)
    )
    if pref is None:
        pref = NotificationPreference(
            organization_id=org_id, user_id=user_id, prefs={}
        )
        db.add(pref)
        await db.flush()
    return pref


def _to_response(pref: NotificationPreference) -> NotificationPreferencesResponse:
    prefs = {
        k: ChannelPreference(
            email=bool(v.get("email", True)),
            in_app=bool(v.get("in_app", True)),
        )
        for k, v in (pref.prefs or {}).items()
    }
    return NotificationPreferencesResponse(
        user_id=pref.user_id,
        organization_id=pref.organization_id,
        prefs=prefs,
    )


def _authorize_read(current: User, target_user_id: uuid.UUID) -> None:
    if current.id == target_user_id:
        return
    if current.role == UserRole.ADMIN:
        return
    raise ForbiddenError("You cannot view another user's preferences.")


def _authorize_write(current: User, target_user_id: uuid.UUID) -> None:
    if current.id == target_user_id:
        return
    if current.role == UserRole.ADMIN:
        return
    raise ForbiddenError("You cannot modify another user's preferences.")


@router.get(
    "/me",
    response_model=NotificationPreferencesResponse,
    summary="Get the current user's notification preferences.",
)
async def get_my_prefs(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationPreferencesResponse:
    pref = await _load_or_create(db, user.organization_id, user.id)
    await db.commit()
    return _to_response(pref)


@router.put(
    "/me",
    response_model=NotificationPreferencesResponse,
    summary="Update the current user's notification preferences.",
)
async def update_my_prefs(
    payload: NotificationPreferencesUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationPreferencesResponse:
    pref = await _load_or_create(db, user.organization_id, user.id)
    pref.prefs = {
        k: {"email": v.email, "in_app": v.in_app}
        for k, v in payload.prefs.items()
    }
    await db.commit()
    await db.refresh(pref)
    return _to_response(pref)


@router.get(
    "/{user_id}",
    response_model=NotificationPreferencesResponse,
    summary="Admin: get another user's preferences.",
)
async def get_user_prefs(
    user_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationPreferencesResponse:
    _authorize_read(user, user_id)

    target = await db.scalar(
        select(User).where(
            User.id == user_id, User.organization_id == user.organization_id
        )
    )
    if target is None:
        raise NotFoundError("User not found.")

    pref = await _load_or_create(db, user.organization_id, user_id)
    await db.commit()
    return _to_response(pref)