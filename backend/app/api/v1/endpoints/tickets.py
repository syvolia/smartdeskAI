"""Ticket endpoints."""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.db.session import get_db
from app.models import Ticket, TicketComment, User
from app.notifications.factory import get_notification_service
from app.notifications.service import NotificationService
from app.repositories.ticket_repository import TicketFilters
from app.schemas.ticket import (
    SortField,
    SortOrder,
    TicketAssignRequest,
    TicketCommentCreateRequest,
    TicketCommentListResponse,
    TicketCommentResponse,
    TicketCreateRequest,
    TicketEventListResponse,
    TicketEventResponse,
    TicketListResponse,
    TicketPriorityChangeRequest,
    TicketResponse,
    TicketStatusChangeRequest,
    TicketUpdateRequest,
)
from app.services.sla_service import SLAService
from app.services.ticket_service import TicketService

router = APIRouter(prefix="/tickets", tags=["tickets"])


# ---------- serializers ----------


def _sla_block(ticket: Ticket) -> dict:
    snap = SLAService.evaluate(ticket)
    return {
        "policy_id": snap.policy_id,
        "policy_name": snap.policy_name,
        "first_response_due_at": snap.first_response_due_at,
        "first_response_at": snap.first_response_at,
        "resolution_due_at": snap.resolution_due_at,
        "resolved_at": snap.resolved_at,
        "first_response_breached": snap.first_response_breached,
        "resolution_breached": snap.resolution_breached,
        "sla_breached": snap.sla_breached,
        "first_response_time_seconds": snap.first_response_time_seconds,
        "resolution_time_seconds": snap.resolution_time_seconds,
    }


def to_ticket_response(ticket: Ticket) -> TicketResponse:
    return TicketResponse(
        id=ticket.id,
        organization_id=ticket.organization_id,
        title=ticket.title,
        description=ticket.description,
        status=ticket.status,
        priority=ticket.priority,
        source=ticket.source,
        customer=ticket.customer,
        assigned_agent=ticket.assigned_agent,
        team=ticket.team,
        category=ticket.category,
        sla=_sla_block(ticket),
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        resolved_at=ticket.resolved_at,
        closed_at=ticket.closed_at,
    )


def to_comment_response(c: TicketComment) -> TicketCommentResponse:
    return TicketCommentResponse(
        id=c.id,
        organization_id=c.organization_id,
        ticket_id=c.ticket_id,
        author=c.author,
        body=c.body,
        is_internal=c.is_internal,
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


def to_event_response(e) -> TicketEventResponse:
    return TicketEventResponse(
        id=e.id,
        organization_id=e.organization_id,
        ticket_id=e.ticket_id,
        actor=e.actor,
        event_type=e.event_type,
        from_value=e.from_value,
        to_value=e.to_value,
        note=e.note,
        details=e.details,
        created_at=e.created_at,
    )


# ---------- endpoints ----------


@router.post(
    "",
    response_model=TicketResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a ticket.",
)
async def create_ticket(
    payload: TicketCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    notifications: NotificationService = Depends(get_notification_service),
) -> TicketResponse:
    service = TicketService(db, notifications=notifications)
    ticket = await service.create(user, payload)
    await db.commit()
    return to_ticket_response(ticket)


@router.get(
    "",
    response_model=TicketListResponse,
    summary="List, filter, sort, paginate, and search tickets.",
)
async def list_tickets(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    status_: Annotated[list[str] | None, Query(alias="status")] = None,
    priority: Annotated[list[str] | None, Query()] = None,
    assigned_agent_id: uuid.UUID | None = None,
    team_id: uuid.UUID | None = None,
    customer_id: uuid.UUID | None = None,
    category_id: uuid.UUID | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    search: str | None = Query(default=None, max_length=200),
    sort: SortField = "created_at",
    order: SortOrder = "desc",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> TicketListResponse:
    from app.models import TicketPriority, TicketStatus

    filters = TicketFilters(
        statuses=[TicketStatus(s) for s in (status_ or [])],
        priorities=[TicketPriority(p) for p in (priority or [])],
        assigned_agent_id=assigned_agent_id,
        team_id=team_id,
        customer_id=customer_id,
        category_id=category_id,
        created_from=created_from,
        created_to=created_to,
        search=search,
    )

    service = TicketService(db)
    rows, total = await service.list_tickets(
        user,
        filters=filters,
        sort=sort,
        order=order,
        page=page,
        page_size=page_size,
    )

    pages = (total + page_size - 1) // page_size if page_size else 0
    return TicketListResponse(
        items=[to_ticket_response(t) for t in rows],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get(
    "/{ticket_id}",
    response_model=TicketResponse,
    summary="Get a single ticket.",
)
async def get_ticket(
    ticket_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TicketResponse:
    service = TicketService(db)
    ticket = await service.get(ticket_id, user)
    return to_ticket_response(ticket)


@router.patch(
    "/{ticket_id}",
    response_model=TicketResponse,
    summary="Update ticket fields (title, description, category).",
)
async def update_ticket(
    ticket_id: uuid.UUID,
    payload: TicketUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TicketResponse:
    service = TicketService(db)
    ticket = await service.update(ticket_id, user, payload)
    await db.commit()
    return to_ticket_response(ticket)


@router.delete(
    "/{ticket_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a ticket (admin only).",
)
async def delete_ticket(
    ticket_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    service = TicketService(db)
    await service.delete(ticket_id, user)
    await db.commit()


@router.post(
    "/{ticket_id}/assign",
    response_model=TicketResponse,
    summary="Assign or reassign a ticket to an agent and/or team.",
)
async def assign_ticket(
    ticket_id: uuid.UUID,
    payload: TicketAssignRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    notifications: NotificationService = Depends(get_notification_service),
) -> TicketResponse:
    service = TicketService(db, notifications=notifications)
    ticket = await service.assign(ticket_id, user, payload)
    await db.commit()
    return to_ticket_response(ticket)


@router.post(
    "/{ticket_id}/status",
    response_model=TicketResponse,
    summary="Change ticket status.",
)
async def change_status(
    ticket_id: uuid.UUID,
    payload: TicketStatusChangeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    notifications: NotificationService = Depends(get_notification_service),
) -> TicketResponse:
    service = TicketService(db, notifications=notifications)
    ticket = await service.change_status(ticket_id, user, payload)
    await db.commit()
    return to_ticket_response(ticket)


@router.post(
    "/{ticket_id}/priority",
    response_model=TicketResponse,
    summary="Change ticket priority (recalculates SLA deadlines).",
)
async def change_priority(
    ticket_id: uuid.UUID,
    payload: TicketPriorityChangeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TicketResponse:
    service = TicketService(db)
    ticket = await service.change_priority(ticket_id, user, payload)
    await db.commit()
    return to_ticket_response(ticket)


@router.post(
    "/{ticket_id}/comments",
    response_model=TicketCommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a comment or internal note.",
)
async def add_comment(
    ticket_id: uuid.UUID,
    payload: TicketCommentCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    notifications: NotificationService = Depends(get_notification_service),
) -> TicketCommentResponse:
    service = TicketService(db, notifications=notifications)
    comment = await service.add_comment(ticket_id, user, payload)
    await db.commit()
    return to_comment_response(comment)


@router.get(
    "/{ticket_id}/comments",
    response_model=TicketCommentListResponse,
    summary="List comments on a ticket.",
)
async def list_comments(
    ticket_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TicketCommentListResponse:
    service = TicketService(db)
    items = await service.list_comments(ticket_id, user)
    return TicketCommentListResponse(
        items=[to_comment_response(c) for c in items],
        total=len(items),
    )


@router.get(
    "/{ticket_id}/events",
    response_model=TicketEventListResponse,
    summary="List ticket activity events (audit trail).",
)
async def list_events(
    ticket_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> TicketEventListResponse:
    service = TicketService(db)
    items, total = await service.list_events(
        ticket_id, user, limit=limit, offset=offset
    )
    return TicketEventListResponse(
        items=[to_event_response(e) for e in items],
        total=total,
    )