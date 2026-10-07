"""Admin API package.

Every router in this package enforces authorization on the server. The
frontend hides admin UI for non-admins, but that is only UX — these
dependencies are what actually restrict access.
"""

from fastapi import APIRouter

from app.api.v1.endpoints.admin import (
    ai_config,
    notification_preferences,
    organization,
    overview,
    slas,
    teams,
    ticket_categories,
    users,
)

router = APIRouter(prefix="/admin", tags=["admin"])
router.include_router(overview.router)
router.include_router(organization.router)
router.include_router(users.router)
router.include_router(teams.router)
router.include_router(ticket_categories.router)
router.include_router(slas.router)
router.include_router(ai_config.router)
router.include_router(notification_preferences.router)