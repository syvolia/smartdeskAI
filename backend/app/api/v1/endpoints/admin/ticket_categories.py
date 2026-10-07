"""Ticket category administration. Reads open to staff, writes to admins."""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.admin._guards import require_admin, require_staff
from app.core.exceptions import ConflictError, NotFoundError
from app.db.session import get_db
from app.models import TicketCategory, User
from app.schemas.admin import (
    TicketCategoryCreateRequest,
    TicketCategoryListResponse,
    TicketCategoryResponse,
    TicketCategoryUpdateRequest,
)

router = APIRouter(prefix="/ticket-categories", tags=["admin"])


@router.get(
    "",
    response_model=TicketCategoryListResponse,
    summary="List ticket categories.",
)
async def list_categories(
    user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> TicketCategoryListResponse:
    rows = list(
        (
            await db.scalars(
                select(TicketCategory)
                .where(TicketCategory.organization_id == user.organization_id)
                .order_by(TicketCategory.name.asc())
            )
        ).all()
    )
    return TicketCategoryListResponse(
        items=[TicketCategoryResponse.model_validate(r) for r in rows],
        total=len(rows),
    )


@router.post(
    "",
    response_model=TicketCategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a ticket category (admin only).",
)
async def create_category(
    payload: TicketCategoryCreateRequest,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> TicketCategoryResponse:
    existing = await db.scalar(
        select(TicketCategory).where(
            TicketCategory.organization_id == user.organization_id,
            TicketCategory.name == payload.name,
        )
    )
    if existing is not None:
        raise ConflictError("A category with this name already exists.")

    category = TicketCategory(
        organization_id=user.organization_id,
        name=payload.name,
        description=payload.description,
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return TicketCategoryResponse.model_validate(category)


@router.patch(
    "/{category_id}",
    response_model=TicketCategoryResponse,
    summary="Update a ticket category (admin only).",
)
async def update_category(
    category_id: uuid.UUID,
    payload: TicketCategoryUpdateRequest,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> TicketCategoryResponse:
    category = await db.scalar(
        select(TicketCategory).where(
            TicketCategory.id == category_id,
            TicketCategory.organization_id == user.organization_id,
        )
    )
    if category is None:
        raise NotFoundError("Category not found.")

    if payload.name is not None:
        category.name = payload.name
    if payload.description is not None:
        category.description = payload.description

    await db.commit()
    await db.refresh(category)
    return TicketCategoryResponse.model_validate(category)


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a ticket category (admin only).",
)
async def delete_category(
    category_id: uuid.UUID,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    category = await db.scalar(
        select(TicketCategory).where(
            TicketCategory.id == category_id,
            TicketCategory.organization_id == user.organization_id,
        )
    )
    if category is None:
        raise NotFoundError("Category not found.")
    await db.delete(category)
    await db.commit()