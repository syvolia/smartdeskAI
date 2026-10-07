"""Admin overview: counts for the dashboard header."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.admin._guards import require_admin
from app.db.session import get_db
from app.models import (
    KnowledgeBaseArticle,
    Organization,
    SLA,
    Team,
    TicketCategory,
    User,
    UserRole,
)
from app.schemas.admin import AdminOverviewResponse

router = APIRouter(tags=["admin"])


@router.get(
    "/overview",
    response_model=AdminOverviewResponse,
    summary="Counts for the admin dashboard.",
)
async def admin_overview(
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AdminOverviewResponse:
    org_id = user.organization_id

    org = await db.get(Organization, org_id)
    assert org is not None  # user.org must exist by FK

    users_count = int(
        await db.scalar(
            select(func.count())
            .select_from(User)
            .where(User.organization_id == org_id)
        )
        or 0
    )
    agents_count = int(
        await db.scalar(
            select(func.count())
            .select_from(User)
            .where(
                User.organization_id == org_id,
                User.role == UserRole.AGENT,
            )
        )
        or 0
    )
    teams_count = int(
        await db.scalar(
            select(func.count())
            .select_from(Team)
            .where(Team.organization_id == org_id)
        )
        or 0
    )
    categories_count = int(
        await db.scalar(
            select(func.count())
            .select_from(TicketCategory)
            .where(TicketCategory.organization_id == org_id)
        )
        or 0
    )
    slas_count = int(
        await db.scalar(
            select(func.count())
            .select_from(SLA)
            .where(SLA.organization_id == org_id)
        )
        or 0
    )
    kb_total = int(
        await db.scalar(
            select(func.count())
            .select_from(KnowledgeBaseArticle)
            .where(KnowledgeBaseArticle.organization_id == org_id)
        )
        or 0
    )
    kb_published = int(
        await db.scalar(
            select(func.count())
            .select_from(KnowledgeBaseArticle)
            .where(
                KnowledgeBaseArticle.organization_id == org_id,
                KnowledgeBaseArticle.status == "PUBLISHED",
            )
        )
        or 0
    )

    ai_enabled = bool(org.ai_config.get("enabled", False))

    return AdminOverviewResponse(
        users=users_count,
        agents=agents_count,
        teams=teams_count,
        categories=categories_count,
        slas=slas_count,
        kb_articles=kb_total,
        kb_published=kb_published,
        plan=org.plan,
        ai_enabled=ai_enabled,
    )