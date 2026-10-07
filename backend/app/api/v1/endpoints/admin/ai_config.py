"""Organization AI configuration (admin only)."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.admin._guards import require_admin
from app.db.session import get_db
from app.models import Organization, User
from app.schemas.admin import AIConfigUpdateRequest, OrganizationProfileResponse

router = APIRouter(prefix="/ai-config", tags=["admin"])

DEFAULT_AI_CONFIG = {
    "enabled": False,
    "auto_summarize": True,
    "auto_classify": False,
    "auto_priority": False,
    "min_confidence": 0.6,
    "suggested_response_tone": "friendly",
}


@router.get(
    "",
    response_model=dict,
    summary="Get the AI configuration for this organization.",
)
async def get_ai_config(
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    org = await db.get(Organization, user.organization_id)
    assert org is not None
    merged = {**DEFAULT_AI_CONFIG, **(org.ai_config or {})}
    return merged


@router.patch(
    "",
    response_model=OrganizationProfileResponse,
    summary="Update the AI configuration.",
)
async def update_ai_config(
    payload: AIConfigUpdateRequest,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> OrganizationProfileResponse:
    org = await db.get(Organization, user.organization_id)
    assert org is not None
    merged = {**DEFAULT_AI_CONFIG, **(org.ai_config or {}), **payload.ai_config}
    org.ai_config = merged
    await db.commit()
    await db.refresh(org)
    return OrganizationProfileResponse.model_validate(org)