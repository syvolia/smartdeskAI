"""SLA administration. Reads open to staff, writes to admins."""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.admin._guards import require_admin, require_staff
from app.core.exceptions import ConflictError, NotFoundError
from app.db.session import get_db
from app.models import SLA, User
from app.schemas.admin import (
    SLACreateRequest,
    SLAListResponse,
    SLAResponse,
    SLAUpdateRequest,
)

router = APIRouter(prefix="/slas", tags=["admin"])


@router.get("", response_model=SLAListResponse, summary="List SLA policies.")
async def list_slas(
    user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> SLAListResponse:
    rows = list(
        (
            await db.scalars(
                select(SLA)
                .where(SLA.organization_id == user.organization_id)
                .order_by(SLA.name.asc())
            )
        ).all()
    )
    return SLAListResponse(
        items=[SLAResponse.model_validate(r) for r in rows],
        total=len(rows),
    )


@router.post(
    "",
    response_model=SLAResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an SLA policy (admin only).",
)
async def create_sla(
    payload: SLACreateRequest,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> SLAResponse:
    existing = await db.scalar(
        select(SLA).where(
            SLA.organization_id == user.organization_id, SLA.name == payload.name
        )
    )
    if existing is not None:
        raise ConflictError("An SLA with this name already exists.")

    sla = SLA(
        organization_id=user.organization_id,
        name=payload.name,
        priority=payload.priority,
        first_response_minutes=payload.first_response_minutes,
        resolution_minutes=payload.resolution_minutes,
        is_active=payload.is_active,
    )
    db.add(sla)
    await db.commit()
    await db.refresh(sla)
    return SLAResponse.model_validate(sla)


@router.patch(
    "/{sla_id}",
    response_model=SLAResponse,
    summary="Update an SLA policy (admin only).",
)
async def update_sla(
    sla_id: uuid.UUID,
    payload: SLAUpdateRequest,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> SLAResponse:
    sla = await db.scalar(
        select(SLA).where(
            SLA.id == sla_id, SLA.organization_id == user.organization_id
        )
    )
    if sla is None:
        raise NotFoundError("SLA not found.")

    if payload.name is not None:
        sla.name = payload.name
    if payload.priority is not None:
        sla.priority = payload.priority
    if payload.first_response_minutes is not None:
        sla.first_response_minutes = payload.first_response_minutes
    if payload.resolution_minutes is not None:
        sla.resolution_minutes = payload.resolution_minutes
    if payload.is_active is not None:
        sla.is_active = payload.is_active

    await db.commit()
    await db.refresh(sla)
    return SLAResponse.model_validate(sla)


@router.delete(
    "/{sla_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an SLA policy (admin only).",
)
async def delete_sla(
    sla_id: uuid.UUID,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    sla = await db.scalar(
        select(SLA).where(
            SLA.id == sla_id, SLA.organization_id == user.organization_id
        )
    )
    if sla is None:
        raise NotFoundError("SLA not found.")
    await db.delete(sla)
    await db.commit()