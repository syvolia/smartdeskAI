"""Aggregate router for API v1."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin,
    ai,
    ai_knowledge,
    analytics,
    auth,
    customers,
    health,
    notifications,
    tickets,
    ws,
    attachments,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(tickets.router)
api_router.include_router(customers.router)
api_router.include_router(ai.router)
api_router.include_router(ai_knowledge.router)
api_router.include_router(analytics.router)
api_router.include_router(notifications.router)
api_router.include_router(admin.router)
api_router.include_router(ws.router)
api_router.include_router(attachments.router)