"""In-process connection registry.

Groups live WebSocket connections by organization and applies per-event
authorization filters before delivery:

- Notification events → only the target user
- Ticket events → all staff in the org; customers only for their own
  tickets, matched by customer email on the event

The manager never queries the database during broadcast; all authorization
decisions use data already on the connection or the event.
"""

import uuid
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from fastapi import WebSocket

from app.core.logging import get_logger
from app.models import UserRole
from app.realtime.schemas import EventType, RealtimeEvent

logger = get_logger(__name__)


@dataclass(eq=False)
class Connection:
    websocket: WebSocket
    user_id: uuid.UUID
    user_email: str
    organization_id: uuid.UUID
    role: UserRole

    def __hash__(self) -> int:  # allow use in sets
        return id(self)


class ConnectionManager:
    def __init__(self) -> None:
        self._by_org: dict[uuid.UUID, set[Connection]] = {}

    # ---------- lifecycle ----------

    async def connect(
        self,
        websocket: WebSocket,
        *,
        user_id: uuid.UUID,
        user_email: str,
        organization_id: uuid.UUID,
        role: UserRole,
    ) -> Connection:
        await websocket.accept()
        conn = Connection(
            websocket=websocket,
            user_id=user_id,
            user_email=user_email,
            organization_id=organization_id,
            role=role,
        )
        self._by_org.setdefault(organization_id, set()).add(conn)
        logger.info(
            "ws_connected",
            user_id=str(user_id),
            org_id=str(organization_id),
            role=role.value,
            total_for_org=len(self._by_org[organization_id]),
        )
        return conn

    async def disconnect(self, conn: Connection) -> None:
        conns = self._by_org.get(conn.organization_id)
        if conns is None:
            return
        conns.discard(conn)
        if not conns:
            self._by_org.pop(conn.organization_id, None)
        logger.info(
            "ws_disconnected",
            user_id=str(conn.user_id),
            org_id=str(conn.organization_id),
        )

    # ---------- delivery ----------

    async def broadcast(self, event: RealtimeEvent) -> int:
        conns = self._by_org.get(event.organization_id)
        if not conns:
            return 0

        delivered = 0
        dead: list[Connection] = []

        for conn in list(conns):
            if not self._may_receive(conn, event):
                continue
            try:
                await conn.websocket.send_json(
                    {"kind": "event", "event": event.to_wire()}
                )
                delivered += 1
            except Exception:
                dead.append(conn)

        for conn in dead:
            await self.disconnect(conn)

        if delivered:
            logger.info(
                "ws_event_delivered",
                type=event.type.value,
                org_id=str(event.organization_id),
                delivered=delivered,
            )
        return delivered

    async def send_to_connection(
        self, conn: Connection, payload: dict[str, Any]
    ) -> None:
        await conn.websocket.send_json(payload)

    # ---------- authorization ----------

    @staticmethod
    def _may_receive(conn: Connection, event: RealtimeEvent) -> bool:
        # Notification events are user-targeted.
        if event.type == EventType.NOTIFICATION_CREATED:
            return event.target_user_id == conn.user_id

        # Ticket events go to staff, and to the ticket's customer.
        if conn.role in (UserRole.ADMIN, UserRole.AGENT):
            return True
        if event.ticket_customer_email is None:
            return False
        return event.ticket_customer_email.lower() == conn.user_email.lower()


@lru_cache(maxsize=1)
def get_connection_manager() -> ConnectionManager:
    return ConnectionManager()