"""Organization profile management (admin only)."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.admin._guards import require_admin
from app.db.session import get_db
from app.models import Organization, User
from app.schemas.admin import (
    OrganizationProfileResponse,
    OrganizationUpdateRequest,
)

router = APIRouter(prefix="/organization", tags=["admin"])


@router.get(
    "",
    response_model=OrganizationProfileResponse,
    summary="Get the current organization's profile.",
)
async def get_profile(
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> OrganizationProfileResponse:
    org = await db.get(Organization, user.organization_id)
    assert org is not None
    return OrganizationProfileResponse.model_validate(org)


@router.patch(
    "",
    response_model=OrganizationProfileResponse,
    summary="Update the current organization's profile.",
)
async def update_profile(
    payload: OrganizationUpdateRequest,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> OrganizationProfileResponse:
    org = await db.get(Organization, user.organization_id)
    assert org is not None

    if payload.name is not None:
        org.name = payload.name
    if payload.plan is not None:
        org.plan = payload.plan
    if payload.settings is not None:
        # Merge — settings keys the client doesn't send are preserved.
        merged = dict(org.settings or {})
        merged.update(payload.settings)
        org.settings = merged

    await db.commit()
    await db.refresh(org)
    return OrganizationProfileResponse.model_validate(org)