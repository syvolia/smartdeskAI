"""Analytics endpoints."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.core.exceptions import ForbiddenError, ValidationError
from app.db.session import get_db
from app.models import User, UserRole
from app.schemas.analytics import AnalyticsDashboard
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _require_staff(user: User) -> None:
    if user.role not in (UserRole.ADMIN, UserRole.AGENT):
        raise ForbiddenError("Analytics are available to staff only.")


@router.get(
    "/dashboard",
    response_model=AnalyticsDashboard,
    summary="Organization-wide analytics dashboard.",
)
async def dashboard(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
    granularity: Annotated[str, Query(pattern="^(day|week|month)$")] = "day",
) -> AnalyticsDashboard:
    _require_staff(user)
    try:
        start, end = AnalyticsService.resolve_date_range(date_from, date_to)
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc

    service = AnalyticsService(db)
    return await service.dashboard(
        user.organization_id, start, end, granularity=granularity
    )