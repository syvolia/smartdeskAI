"""Wire format for real-time events.

Events are self-contained: a client that receives one has enough data to
decide which REST queries to invalidate. The payload is intentionally
small — the REST API remains the source of truth.

Every event has a unique `id`. Clients track recently-seen ids and drop
duplicates that could arise from retries or multi-path delivery.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EventType(str, Enum):
    TICKET_COMMENT_CREATED = "ticket.comment_created"
    TICKET_STATUS_CHANGED = "ticket.status_changed"
    TICKET_PRIORITY_CHANGED = "ticket.priority_changed"
    TICKET_ASSIGNED = "ticket.assigned"
    TICKET_REASSIGNED = "ticket.reassigned"
    TICKET_CREATED = "ticket.created"
    TICKET_UPDATED = "ticket.updated"
    TICKET_RESOLVED = "ticket.resolved"
    TICKET_REOPENED = "ticket.reopened"
    NOTIFICATION_CREATED = "notification.created"


class RealtimeEvent(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    type: EventType
    organization_id: uuid.UUID
    occurred_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    actor_user_id: uuid.UUID | None = None

    # Ticket-scoped events
    ticket_id: uuid.UUID | None = None
    ticket_customer_email: str | None = None

    # Notification-scoped events
    target_user_id: uuid.UUID | None = None

    payload: dict[str, Any] = Field(default_factory=dict)

    def to_wire(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    @classmethod
    def from_wire(cls, data: dict[str, Any]) -> "RealtimeEvent":
        return cls.model_validate(data)