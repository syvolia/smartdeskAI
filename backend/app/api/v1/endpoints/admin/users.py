"""User administration (admin only).

Every route is guarded by `require_admin`, which is the actual
authorization boundary. The frontend hides admin navigation for
non-admins, but that's UX — a non-admin hitting these endpoints gets 403
regardless of what the browser shows.

The create-user route applies the password policy before hashing.
"""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.admin._guards import require_admin
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.password_policy import validate_password_strength
from app.core.rate_limit import rate_limit
from app.core.security import hash_password
from app.db.session import get_db
from app.models import User, UserRole
from app.schemas.admin import (
    AdminUserCreateRequest,
    AdminUserListResponse,
    AdminUserResponse,
    AdminUserUpdateRequest,
)

router = APIRouter(prefix="/users", tags=["admin"])


@router.get(
    "",
    response_model=AdminUserListResponse,
    dependencies=[Depends(rate_limit("admin:users:read", 120, 60))],
    summary="List users in the organization.",
)
async def list_users(
    role: UserRole | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    search: str | None = Query(default=None, max_length=200),
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AdminUserListResponse:
    stmt = select(User).where(User.organization_id == user.organization_id)
    if role is not None:
        stmt = stmt.where(User.role == role)
    if is_active is not None:
        stmt = stmt.where(User.is_active.is_(is_active))
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            (User.email.ilike(pattern)) | (User.full_name.ilike(pattern))
        )
    stmt = stmt.order_by(User.full_name.asc())
    rows = list((await db.scalars(stmt)).all())
    return AdminUserListResponse(
        items=[AdminUserResponse.model_validate(r) for r in rows],
        total=len(rows),
    )


@router.post(
    "",
    response_model=AdminUserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("admin:users:create", 30, 3600))],
    summary="Create a user in the organization.",
)
async def create_user(
    payload: AdminUserCreateRequest,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AdminUserResponse:
    # Enforce the same password policy as public registration.
    validate_password_strength(payload.password, email=payload.email)

    existing = await db.scalar(select(User).where(User.email == payload.email))
    if existing is not None:
        raise ConflictError("A user with this email already exists.")

    new_user = User(
        organization_id=user.organization_id,
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        is_active=True,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return AdminUserResponse.model_validate(new_user)


@router.patch(
    "/{user_id}",
    response_model=AdminUserResponse,
    dependencies=[Depends(rate_limit("admin:users:write", 120, 60))],
    summary="Update a user's name, role, or active status.",
)
async def update_user(
    user_id: uuid.UUID,
    payload: AdminUserUpdateRequest,
    actor: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AdminUserResponse:
    target = await db.scalar(
        select(User).where(
            User.id == user_id,
            User.organization_id == actor.organization_id,
        )
    )
    if target is None:
        raise NotFoundError("User not found.")

    # Guardrails: don't let the last admin demote or deactivate themselves.
    if target.id == actor.id:
        if payload.role is not None and payload.role != actor.role:
            raise ValidationError("You cannot change your own role.")
        if payload.is_active is False:
            raise ValidationError("You cannot deactivate your own account.")

    if payload.full_name is not None:
        target.full_name = payload.full_name
    if payload.role is not None:
        target.role = payload.role
    if payload.is_active is not None:
        target.is_active = payload.is_active

    await db.commit()
    await db.refresh(target)
    return AdminUserResponse.model_validate(target)