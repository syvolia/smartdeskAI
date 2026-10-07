"""Convenience publishers called by domain services.

These functions accept already-loaded ORM objects and build the wire event.
They never query the database — callers pass everything needed.
"""

import uuid

from app.models import Notification, Ticket, TicketComment
from app.realtime.bus import get_realtime_bus
from app.realtime.schemas import EventType, RealtimeEvent


async def publish_notification(notification: Notification) -> None:
    """Publish a user-targeted notification event."""
    await get_realtime_bus().publish(
        RealtimeEvent(
            type=EventType.NOTIFICATION_CREATED,
            organization_id=notification.organization_id,
            target_user_id=notification.user_id,
            payload={
                "notification_id": str(notification.id),
                "notification_type": notification.type.value,
                "title": notification.title,
                "entity_type": notification.entity_type,
                "entity_id": str(notification.entity_id)
                if notification.entity_id
                else None,
            },
        )
    )


async def publish_ticket_event(
    *,
    event_type: EventType,
    ticket: Ticket,
    actor_user_id: uuid.UUID | None,
    payload: dict | None = None,
    customer_email: str | None = None,
) -> None:
    """Publish a ticket-scoped event.

    `customer_email` is the ticket's customer's email (string, lowercased).
    Delivery to CUSTOMER connections relies on it — no DB hit required.
    """
    await get_realtime_bus().publish(
        RealtimeEvent(
            type=event_type,
            organization_id=ticket.organization_id,
            ticket_id=ticket.id,
            actor_user_id=actor_user_id,
            ticket_customer_email=(customer_email or "").lower() or None,
            payload=payload or {},
        )
    )


async def publish_ticket_comment(
    *, ticket: Ticket, comment: TicketComment, actor_user_id: uuid.UUID, customer_email: str
) -> None:
    await publish_ticket_event(
        event_type=EventType.TICKET_COMMENT_CREATED,
        ticket=ticket,
        actor_user_id=actor_user_id,
        customer_email=customer_email,
        payload={
            "comment_id": str(comment.id),
            "is_internal": comment.is_internal,
        },
    )


async def publish_ticket_status(
    *,
    ticket: Ticket,
    actor_user_id: uuid.UUID,
    from_status: str,
    to_status: str,
    customer_email: str,
) -> None:
    event_type = EventType.TICKET_STATUS_CHANGED
    if to_status == "RESOLVED":
        event_type = EventType.TICKET_RESOLVED
    elif to_status == "CLOSED":
        event_type = EventType.TICKET_STATUS_CHANGED  # or a dedicated CLOSED
    elif from_status in ("RESOLVED", "CLOSED"):
        event_type = EventType.TICKET_REOPENED

    await publish_ticket_event(
        event_type=event_type,
        ticket=ticket,
        actor_user_id=actor_user_id,
        customer_email=customer_email,
        payload={"from": from_status, "to": to_status},
    )


async def publish_ticket_assignment(
    *,
    ticket: Ticket,
    actor_user_id: uuid.UUID,
    previous_assignee_id: uuid.UUID | None,
    customer_email: str,
) -> None:
    event_type = (
        EventType.TICKET_REASSIGNED
        if previous_assignee_id is not None
        else EventType.TICKET_ASSIGNED
    )
    await publish_ticket_event(
        event_type=event_type,
        ticket=ticket,
        actor_user_id=actor_user_id,
        customer_email=customer_email,
        payload={
            "assigned_agent_id": str(ticket.assigned_agent_id)
            if ticket.assigned_agent_id
            else None,
            "previous_assignee_id": str(previous_assignee_id)
            if previous_assignee_id
            else None,
            "team_id": str(ticket.team_id) if ticket.team_id else None,
        },
    )