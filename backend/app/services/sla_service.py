"""SLA policy resolution, deadline computation, and breach evaluation."""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SLA, Ticket, TicketPriority, TicketStatus
from app.repositories.ticket_repository import TicketRepository


@dataclass
class SLASnapshot:
    policy_id: uuid.UUID | None
    policy_name: str | None
    first_response_due_at: datetime | None
    first_response_at: datetime | None
    resolution_due_at: datetime | None
    resolved_at: datetime | None
    first_response_breached: bool
    resolution_breached: bool
    sla_breached: bool
    first_response_time_seconds: int | None
    resolution_time_seconds: int | None


def _marker(actual: datetime | None, fallback: datetime) -> datetime:
    return actual if actual is not None else fallback


class SLAService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = TicketRepository(db)

    async def resolve_policy(
        self, org_id: uuid.UUID, priority: TicketPriority
    ) -> SLA | None:
        return await self.repo.find_sla_policy(org_id, priority)

    async def apply_policy(self, ticket: Ticket) -> SLA | None:
        """Set or clear SLA fields on the ticket based on its priority.

        Deadlines are always relative to ticket.created_at, which is the
        standard SLA anchoring point.
        """
        policy = await self.resolve_policy(ticket.organization_id, ticket.priority)
        base = ticket.created_at or datetime.now(timezone.utc)

        if policy is None:
            ticket.sla_policy_id = None
            ticket.first_response_due_at = None
            ticket.resolution_due_at = None
        else:
            ticket.sla_policy_id = policy.id
            ticket.first_response_due_at = base + timedelta(
                minutes=policy.first_response_minutes
            )
            ticket.resolution_due_at = base + timedelta(
                minutes=policy.resolution_minutes
            )
        return policy

    @staticmethod
    def evaluate(ticket: Ticket, *, now: datetime | None = None) -> SLASnapshot:
        now = now or datetime.now(timezone.utc)

        first_response_breached = False
        if ticket.first_response_due_at is not None:
            if ticket.first_response_at is not None:
                marker = ticket.first_response_at
            elif ticket.resolved_at is not None:
                marker = ticket.resolved_at
            else:
                marker = now
            first_response_breached = marker > ticket.first_response_due_at

        resolution_breached = False
        if ticket.resolution_due_at is not None:
            marker = ticket.resolved_at or now
            resolution_breached = marker > ticket.resolution_due_at

        fr_time = None
        if ticket.first_response_at and ticket.created_at:
            fr_time = int(
                (ticket.first_response_at - ticket.created_at).total_seconds()
            )

        res_time = None
        if ticket.resolved_at and ticket.created_at:
            res_time = int((ticket.resolved_at - ticket.created_at).total_seconds())

        policy_name = ticket.sla_policy.name if ticket.sla_policy else None

        return SLASnapshot(
            policy_id=ticket.sla_policy_id,
            policy_name=policy_name,
            first_response_due_at=ticket.first_response_due_at,
            first_response_at=ticket.first_response_at,
            resolution_due_at=ticket.resolution_due_at,
            resolved_at=ticket.resolved_at,
            first_response_breached=first_response_breached,
            resolution_breached=resolution_breached,
            sla_breached=first_response_breached or resolution_breached,
            first_response_time_seconds=fr_time,
            resolution_time_seconds=res_time,
        )


__all__ = ["SLAService", "SLASnapshot"]