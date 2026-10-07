"""Notification service — the single entry point the ticket domain uses.

Every method here corresponds to a domain event. The service:

1. Resolves recipients.
2. Builds a `NotificationMessage` per recipient (with dedupe keys).
3. Fans out to every registered channel.
4. Uses Redis to dedupe within a time window.

Callers don't know or care what channels exist.
"""

import uuid

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models import Ticket, TicketComment, User
from app.models.enums import NotificationType
from app.notifications.base import NotificationChannel, NotificationMessage
from app.notifications.recipients import RecipientResolver

logger = get_logger(__name__)

DEDUPE_PREFIX = "notif:dedupe:"
DEDUPE_TTL_SECONDS = 300  # 5 minutes


class NotificationService:
    def __init__(
        self,
        *,
        db: AsyncSession,
        redis: Redis,
        channels: list[NotificationChannel],
    ) -> None:
        self.db = db
        self.redis = redis
        self.channels = channels
        self.recipients = RecipientResolver(db)

    # ---------- dispatch ----------

    async def dispatch(self, messages: list[NotificationMessage]) -> int:
        """Deliver messages through every channel. Returns delivered count."""
        delivered = 0
        for message in messages:
            if message.dedupe_key is not None:
                claimed = await self._claim_dedupe(message)
                if not claimed:
                    logger.info(
                        "notification_deduped",
                        type=message.type.value,
                        user_id=str(message.user_id),
                        dedupe_key=message.dedupe_key,
                    )
                    continue

            for channel in self.channels:
                try:
                    await channel.deliver(message)
                    delivered += 1
                except Exception:
                    logger.exception(
                        "notification_channel_failed",
                        channel=channel.name,
                        type=message.type.value,
                    )
        return delivered

    async def _claim_dedupe(self, message: NotificationMessage) -> bool:
        key = f"{DEDUPE_PREFIX}{message.dedupe_key}"
        try:
            # SET NX EX: returns True only if the key was absent.
            result = await self.redis.set(key, "1", nx=True, ex=DEDUPE_TTL_SECONDS)
            return bool(result)
        except Exception:
            # If Redis is down, don't lose notifications — allow delivery.
            logger.warning("dedupe_redis_error_allowing_delivery")
            return True

    # ---------- typed event handlers ----------

    async def on_ticket_assigned(
        self, ticket: Ticket, actor: User
    ) -> None:
        recipients = await self.recipients.for_assignee(
            assignee_id=ticket.assigned_agent_id, actor_id=actor.id
        )
        messages = [
            self._ticket_message(
                ticket=ticket,
                user_id=uid,
                type=NotificationType.TICKET_ASSIGNED,
                title="Ticket assigned to you",
                body=f"{actor.full_name} assigned you #{str(ticket.id)[:8]} — {ticket.title}",
                dedupe_key=f"assign:{ticket.id}:{uid}",
            )
            for uid in recipients
        ]
        await self.dispatch(messages)

    async def on_ticket_reassigned(
        self,
        ticket: Ticket,
        actor: User,
        *,
        previous_assignee_id: uuid.UUID | None,
    ) -> None:
        recipients = await self.recipients.for_reassignment(
            previous_assignee_id=previous_assignee_id,
            new_assignee_id=ticket.assigned_agent_id,
            actor_id=actor.id,
        )
        messages = [
            self._ticket_message(
                ticket=ticket,
                user_id=uid,
                type=NotificationType.TICKET_REASSIGNED,
                title="Ticket reassigned",
                body=f"{actor.full_name} reassigned #{str(ticket.id)[:8]} — {ticket.title}",
                dedupe_key=f"reassign:{ticket.id}:{uid}:{ticket.assigned_agent_id}",
            )
            for uid in recipients
        ]
        await self.dispatch(messages)

    async def on_comment_added(
        self, ticket: Ticket, comment: TicketComment, actor: User
    ) -> None:
        recipients = await self.recipients.for_comment(
            ticket_assignee_id=ticket.assigned_agent_id,
            team_id=ticket.team_id,
            commenter_id=actor.id,
            is_internal=comment.is_internal,
        )
        kind = "note" if comment.is_internal else "reply"
        messages = [
            self._ticket_message(
                ticket=ticket,
                user_id=uid,
                type=NotificationType.TICKET_COMMENT,
                title=f"New {kind} on #{str(ticket.id)[:8]}",
                body=f"{actor.full_name} commented on {ticket.title}",
                dedupe_key=None,  # comments should always notify
            )
            for uid in recipients
        ]
        await self.dispatch(messages)

    async def on_ticket_resolved(self, ticket: Ticket, actor: User) -> None:
        recipients = await self.recipients.for_status_change(
            ticket_assignee_id=ticket.assigned_agent_id, actor_id=actor.id
        )
        messages = [
            self._ticket_message(
                ticket=ticket,
                user_id=uid,
                type=NotificationType.TICKET_RESOLVED,
                title="Ticket resolved",
                body=f"{actor.full_name} resolved #{str(ticket.id)[:8]} — {ticket.title}",
                dedupe_key=f"resolved:{ticket.id}:{uid}",
            )
            for uid in recipients
        ]
        await self.dispatch(messages)

    async def on_ticket_reopened(self, ticket: Ticket, actor: User) -> None:
        recipients = await self.recipients.for_status_change(
            ticket_assignee_id=ticket.assigned_agent_id, actor_id=actor.id
        )
        messages = [
            self._ticket_message(
                ticket=ticket,
                user_id=uid,
                type=NotificationType.TICKET_REOPENED,
                title="Ticket reopened",
                body=f"{actor.full_name} reopened #{str(ticket.id)[:8]} — {ticket.title}",
                dedupe_key=f"reopened:{ticket.id}:{uid}",
            )
            for uid in recipients
        ]
        await self.dispatch(messages)

    async def on_sla_warning(self, ticket: Ticket) -> None:
        recipients = await self.recipients.for_sla(
            ticket_assignee_id=ticket.assigned_agent_id,
            org_id=ticket.organization_id,
        )
        messages = [
            self._ticket_message(
                ticket=ticket,
                user_id=uid,
                type=NotificationType.SLA_WARNING,
                title="SLA approaching breach",
                body=f"#{str(ticket.id)[:8]} — {ticket.title} is nearing its SLA deadline",
                dedupe_key=f"sla-warn:{ticket.id}:{uid}",
            )
            for uid in recipients
        ]
        await self.dispatch(messages)

    async def on_sla_breached(self, ticket: Ticket) -> None:
        recipients = await self.recipients.for_sla(
            ticket_assignee_id=ticket.assigned_agent_id,
            org_id=ticket.organization_id,
        )
        messages = [
            self._ticket_message(
                ticket=ticket,
                user_id=uid,
                type=NotificationType.SLA_BREACHED,
                title="SLA breached",
                body=f"#{str(ticket.id)[:8]} — {ticket.title} has breached its SLA",
                dedupe_key=f"sla-breach:{ticket.id}:{uid}",
            )
            for uid in recipients
        ]
        await self.dispatch(messages)

    # ---------- helpers ----------

    @staticmethod
    def _ticket_message(
        *,
        ticket: Ticket,
        user_id: uuid.UUID,
        type: NotificationType,
        title: str,
        body: str,
        dedupe_key: str | None,
    ) -> NotificationMessage:
        return NotificationMessage(
            organization_id=ticket.organization_id,
            user_id=user_id,
            type=type,
            title=title,
            body=body,
            entity_type="ticket",
            entity_id=ticket.id,
            dedupe_key=dedupe_key,
        )