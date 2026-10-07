"""Tenant-scoped ticket data access."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Customer, Ticket, TicketPriority, TicketStatus

_TICKET_EAGER = (
    selectinload(Ticket.customer),
    selectinload(Ticket.assigned_agent),
    selectinload(Ticket.team),
    selectinload(Ticket.category),
    selectinload(Ticket.sla_policy),
)


@dataclass
class TicketFilters:
    statuses: list[TicketStatus] = field(default_factory=list)
    priorities: list[TicketPriority] = field(default_factory=list)
    assigned_agent_id: uuid.UUID | None = None
    team_id: uuid.UUID | None = None
    customer_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None
    search: str | None = None
    restrict_customer_email: str | None = None


class TicketRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # --- point reads ---------------------------------------------------------

    async def get(self, ticket_id: uuid.UUID, org_id: uuid.UUID) -> Ticket | None:
        stmt = (
            select(Ticket)
            .where(Ticket.id == ticket_id, Ticket.organization_id == org_id)
            .options(*_TICKET_EAGER)
        )
        return await self.db.scalar(stmt)

    # --- writes --------------------------------------------------------------

    async def add(self, ticket: Ticket) -> Ticket:
        self.db.add(ticket)
        await self.db.flush()
        return ticket

    async def delete(self, ticket: Ticket) -> None:
        await self.db.delete(ticket)
        await self.db.flush()

    # --- list ----------------------------------------------------------------

    def _apply_filters(self, stmt, org_id: uuid.UUID, f: TicketFilters):
        stmt = stmt.where(Ticket.organization_id == org_id)

        if f.statuses:
            stmt = stmt.where(Ticket.status.in_(f.statuses))
        if f.priorities:
            stmt = stmt.where(Ticket.priority.in_(f.priorities))
        if f.assigned_agent_id is not None:
            stmt = stmt.where(Ticket.assigned_agent_id == f.assigned_agent_id)
        if f.team_id is not None:
            stmt = stmt.where(Ticket.team_id == f.team_id)
        if f.customer_id is not None:
            stmt = stmt.where(Ticket.customer_id == f.customer_id)
        if f.category_id is not None:
            stmt = stmt.where(Ticket.category_id == f.category_id)
        if f.created_from is not None:
            stmt = stmt.where(Ticket.created_at >= f.created_from)
        if f.created_to is not None:
            stmt = stmt.where(Ticket.created_at <= f.created_to)
        if f.search:
            pattern = f"%{f.search}%"
            stmt = stmt.where(
                or_(Ticket.title.ilike(pattern), Ticket.description.ilike(pattern))
            )
        if f.restrict_customer_email is not None:
            stmt = stmt.where(
                Ticket.customer.has(Customer.email == f.restrict_customer_email)
            )
        return stmt

    async def list_paginated(
        self,
        org_id: uuid.UUID,
        *,
        filters: TicketFilters,
        sort: str,
        order: str,
        page: int,
        page_size: int,
    ) -> tuple[list[Ticket], int]:
        base = select(Ticket)
        base = self._apply_filters(base, org_id, filters)

        count_stmt = select(func.count()).select_from(base.subquery())
        total = int(await self.db.scalar(count_stmt) or 0)

        sortable = {
            "created_at": Ticket.created_at,
            "updated_at": Ticket.updated_at,
            "priority": Ticket.priority,
            "status": Ticket.status,
            "resolved_at": Ticket.resolved_at,
            "title": Ticket.title,
        }
        col = sortable.get(sort, Ticket.created_at)
        order_by = col.asc() if order == "asc" else col.desc()

        offset = (page - 1) * page_size
        stmt = (
            base.options(*_TICKET_EAGER)
            .order_by(order_by, Ticket.id.asc())
            .offset(offset)
            .limit(page_size)
        )
        rows = list((await self.db.scalars(stmt)).all())
        return rows, total

    # --- SLA lookup ----------------------------------------------------------

    async def find_sla_policy(self, org_id: uuid.UUID, priority):
        from app.models import SLA

        return await self.db.scalar(
            select(SLA)
            .where(
                SLA.organization_id == org_id,
                SLA.priority == priority,
                SLA.is_active.is_(True),
            )
            .order_by(SLA.first_response_minutes.asc())
            .limit(1)
        )