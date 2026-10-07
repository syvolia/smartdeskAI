"""Scan for tickets approaching or past SLA deadlines.

Intended to be called by a scheduled job (cron, Celery beat, Kubernetes
CronJob). The HTTP endpoint in `notifications.py` exposes it so the
portfolio demo can trigger it manually — in production it's a background
worker, not a public route.
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models import Ticket, TicketStatus
from app.notifications.service import NotificationService

logger = get_logger(__name__)

WARNING_WINDOW = timedelta(minutes=30)


class SLANotificationScanner:
    def __init__(
        self,
        db: AsyncSession,
        notifications: NotificationService,
    ) -> None:
        self.db = db
        self.notifications = notifications

    async def scan(self, org_id: uuid.UUID | None = None) -> dict:
        """Scan for SLA warning and breach candidates.

        Warning: `resolution_due_at` within the next WARNING_WINDOW and
        the ticket is not yet resolved/closed, and no warning has been sent
        recently (dedupe key prevents repeat notifications).

        Breach: `resolution_due_at` is in the past and `sla_breached`
        hasn't been flagged yet.
        """
        now = datetime.now(timezone.utc)
        warn_cutoff = now + WARNING_WINDOW

        active_states = [
            TicketStatus.OPEN,
            TicketStatus.IN_PROGRESS,
            TicketStatus.WAITING_CUSTOMER,
        ]

        # Warnings: due within the next 30 minutes and not yet breached.
        warn_stmt = select(Ticket).where(
            Ticket.status.in_(active_states),
            Ticket.resolution_due_at.is_not(None),
            Ticket.resolution_due_at > now,
            Ticket.resolution_due_at <= warn_cutoff,
            Ticket.sla_breached.is_(False),
        )
        if org_id is not None:
            warn_stmt = warn_stmt.where(Ticket.organization_id == org_id)
        warnings = list((await self.db.scalars(warn_stmt)).all())

        for ticket in warnings:
            await self.notifications.on_sla_warning(ticket)

        # Breaches: due in the past and not yet flagged.
        breach_stmt = select(Ticket).where(
            Ticket.status.in_(active_states),
            Ticket.resolution_due_at.is_not(None),
            Ticket.resolution_due_at <= now,
            Ticket.sla_breached.is_(False),
        )
        if org_id is not None:
            breach_stmt = breach_stmt.where(Ticket.organization_id == org_id)
        breaches = list((await self.db.scalars(breach_stmt)).all())

        for ticket in breaches:
            ticket.sla_breached = True
            await self.notifications.on_sla_breached(ticket)

        await self.db.flush()

        logger.info(
            "sla_scan_complete",
            warnings=len(warnings),
            breaches=len(breaches),
            org_id=str(org_id) if org_id else None,
        )
        return {"warnings": len(warnings), "breaches": len(breaches)}