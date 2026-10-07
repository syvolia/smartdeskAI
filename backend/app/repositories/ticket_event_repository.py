"""Ticket event log data access."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import TicketEvent, TicketEventType


class TicketEventRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def add(
        self,
        *,
        organization_id: uuid.UUID,
        ticket_id: uuid.UUID,
        actor_user_id: uuid.UUID | None,
        event_type: TicketEventType,
        from_value: str | None = None,
        to_value: str | None = None,
        note: str | None = None,
        details: dict | None = None,
    ) -> TicketEvent:
        event = TicketEvent(
            organization_id=organization_id,
            ticket_id=ticket_id,
            actor_user_id=actor_user_id,
            event_type=event_type,
            from_value=from_value,
            to_value=to_value,
            note=note,
            details=details,
        )
        self.db.add(event)
        await self.db.flush()
        return event

    async def list_for_ticket(
        self,
        ticket_id: uuid.UUID,
        org_id: uuid.UUID,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[TicketEvent], int]:
        base = select(TicketEvent).where(
            TicketEvent.ticket_id == ticket_id,
            TicketEvent.organization_id == org_id,
        )
        total = int(
            await self.db.scalar(
                select(func.count()).select_from(base.subquery())
            )
            or 0
        )
        stmt = (
            base.options(selectinload(TicketEvent.actor))
            .order_by(TicketEvent.created_at.asc(), TicketEvent.id.asc())
            .offset(offset)
            .limit(limit)
        )
        rows = list((await self.db.scalars(stmt)).all())
        return rows, total