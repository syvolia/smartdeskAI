"""AI copilot endpoints.

These routes are intentionally thin: they resolve the AIService via
dependency injection, delegate, and return the suggestion. No business
logic lives here, and no OpenAI call is made directly.

Rate limiting: the generate endpoints are capped per-identity to bound
cost. Read endpoints (list, accept, reject) are lighter and share a
looser budget.
"""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.factory import get_ai_service
from app.ai.service import AIService
from app.api.dependencies.auth import get_current_user
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.models import AISuggestion, User
from app.models.enums import AISuggestionKind
from app.schemas.ai import (
    AIAcceptResponse,
    AIRejectRequest,
    AISuggestionListResponse,
    AISuggestionResponse,
)

router = APIRouter(prefix="/ai", tags=["ai"])


def _to_response(s: AISuggestion) -> AISuggestionResponse:
    return AISuggestionResponse(
        id=s.id,
        organization_id=s.organization_id,
        ticket_id=s.ticket_id,
        kind=s.kind,
        status=s.status,
        payload=s.payload,
        confidence=s.confidence,
        model=s.model,
        created_at=s.created_at,
        updated_at=s.updated_at,
        accepted_at=s.accepted_at,
        rejected_at=s.rejected_at,
        rejection_reason=s.rejection_reason,
    )


# ---------- generate (rate limited: cost-sensitive) ----------


@router.post(
    "/tickets/{ticket_id}/classify",
    response_model=AISuggestionResponse,
    dependencies=[Depends(rate_limit("ai:generate", 30, 60))],
    summary="Suggest a category for a ticket.",
)
async def classify_ticket(
    ticket_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: AIService = Depends(get_ai_service),
    db: AsyncSession = Depends(get_db),
) -> AISuggestionResponse:
    suggestion = await service.classify(ticket_id, user)
    await db.commit()
    return _to_response(suggestion)


@router.post(
    "/tickets/{ticket_id}/suggest-priority",
    response_model=AISuggestionResponse,
    dependencies=[Depends(rate_limit("ai:generate", 30, 60))],
    summary="Suggest a priority for a ticket.",
)
async def suggest_priority(
    ticket_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: AIService = Depends(get_ai_service),
    db: AsyncSession = Depends(get_db),
) -> AISuggestionResponse:
    suggestion = await service.suggest_priority(ticket_id, user)
    await db.commit()
    return _to_response(suggestion)


@router.post(
    "/tickets/{ticket_id}/summarize",
    response_model=AISuggestionResponse,
    dependencies=[Depends(rate_limit("ai:generate", 30, 60))],
    summary="Summarize a ticket conversation for the agent.",
)
async def summarize_ticket(
    ticket_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: AIService = Depends(get_ai_service),
    db: AsyncSession = Depends(get_db),
) -> AISuggestionResponse:
    suggestion = await service.summarize(ticket_id, user)
    await db.commit()
    return _to_response(suggestion)


@router.post(
    "/tickets/{ticket_id}/suggest-response",
    response_model=AISuggestionResponse,
    dependencies=[Depends(rate_limit("ai:generate", 30, 60))],
    summary="Draft a reply for the agent to review.",
)
async def suggest_response(
    ticket_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: AIService = Depends(get_ai_service),
    db: AsyncSession = Depends(get_db),
) -> AISuggestionResponse:
    suggestion = await service.suggest_response(ticket_id, user)
    await db.commit()
    return _to_response(suggestion)


@router.post(
    "/tickets/{ticket_id}/suggest-next-action",
    response_model=AISuggestionResponse,
    dependencies=[Depends(rate_limit("ai:generate", 30, 60))],
    summary="Recommend the next action for the ticket.",
)
async def suggest_next_action(
    ticket_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: AIService = Depends(get_ai_service),
    db: AsyncSession = Depends(get_db),
) -> AISuggestionResponse:
    suggestion = await service.suggest_next_action(ticket_id, user)
    await db.commit()
    return _to_response(suggestion)


# ---------- read + accept / reject (looser budget) ----------


@router.get(
    "/tickets/{ticket_id}/suggestions",
    response_model=AISuggestionListResponse,
    dependencies=[Depends(rate_limit("ai:read", 120, 60))],
    summary="List AI suggestions for a ticket.",
)
async def list_suggestions(
    ticket_id: uuid.UUID,
    kind: AISuggestionKind | None = Query(default=None),
    user: User = Depends(get_current_user),
    service: AIService = Depends(get_ai_service),
) -> AISuggestionListResponse:
    items = await service.list_for_ticket(ticket_id, user, kind=kind)
    return AISuggestionListResponse(
        items=[_to_response(s) for s in items],
        total=len(items),
    )


@router.post(
    "/suggestions/{suggestion_id}/accept",
    response_model=AIAcceptResponse,
    dependencies=[Depends(rate_limit("ai:read", 120, 60))],
    summary="Record that an agent accepted an AI suggestion.",
)
async def accept_suggestion(
    suggestion_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: AIService = Depends(get_ai_service),
    db: AsyncSession = Depends(get_db),
) -> AIAcceptResponse:
    suggestion = await service.accept(suggestion_id, user)
    await db.commit()
    return AIAcceptResponse(suggestion=_to_response(suggestion))


@router.post(
    "/suggestions/{suggestion_id}/reject",
    response_model=AIAcceptResponse,
    dependencies=[Depends(rate_limit("ai:read", 120, 60))],
    summary="Record that an agent rejected an AI suggestion.",
)
async def reject_suggestion(
    suggestion_id: uuid.UUID,
    payload: AIRejectRequest,
    user: User = Depends(get_current_user),
    service: AIService = Depends(get_ai_service),
    db: AsyncSession = Depends(get_db),
) -> AIAcceptResponse:
    suggestion = await service.reject(suggestion_id, user, payload.reason)
    await db.commit()
    return AIAcceptResponse(suggestion=_to_response(suggestion))