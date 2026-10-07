"""Core notification types."""

import uuid
from dataclasses import dataclass, field
from typing import Protocol

from app.models.enums import NotificationType


@dataclass(frozen=True)
class NotificationMessage:
    """A single notification addressed to one user.

    `dedupe_key` prevents duplicate deliveries within a time window. Set it
    to something like `"assign:{ticket_id}:{user_id}"`. If two identical
    dispatches happen inside the dedupe TTL, only the first is delivered.
    """

    organization_id: uuid.UUID
    user_id: uuid.UUID
    type: NotificationType
    title: str
    body: str
    entity_type: str | None = None
    entity_id: uuid.UUID | None = None
    dedupe_key: str | None = None
    metadata: dict = field(default_factory=dict)


class NotificationChannel(Protocol):
    """A delivery mechanism (in-app, email, WebSocket, Slack...)."""

    name: str

    async def deliver(self, message: NotificationMessage) -> None: ...