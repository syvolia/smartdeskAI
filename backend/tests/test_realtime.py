"""Real-time event bus and connection manager tests.

WebSocket transport is exercised with a fake socket that records sent
messages. No actual network is involved.
"""

import uuid
from typing import Any

import pytest

from app.models import UserRole
from app.realtime.manager import Connection, ConnectionManager
from app.realtime.schemas import EventType, RealtimeEvent

pytestmark = pytest.mark.asyncio


class FakeWebSocket:
    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []
        self.accepted = False
        self.closed = False

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, payload: dict) -> None:
        self.sent.append(payload)

    async def close(self, code: int = 1000, reason: str = "") -> None:
        self.closed = True


async def _connect(
    manager: ConnectionManager,
    *,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    email: str,
    role: UserRole,
) -> Connection:
    ws = FakeWebSocket()
    return await manager.connect(
        ws,
        user_id=user_id,
        user_email=email,
        organization_id=org_id,
        role=role,
    )


async def test_staff_receives_ticket_event() -> None:
    manager = ConnectionManager()
    org = uuid.uuid4()
    agent = await _connect(
        manager,
        org_id=org,
        user_id=uuid.uuid4(),
        email="agent@ex.test",
        role=UserRole.AGENT,
    )
    await manager.broadcast(
        RealtimeEvent(
            type=EventType.TICKET_STATUS_CHANGED,
            organization_id=org,
            ticket_id=uuid.uuid4(),
            ticket_customer_email="customer@ex.test",
            payload={"from": "OPEN", "to": "RESOLVED"},
        )
    )
    assert len(agent.websocket.sent) == 1
    assert agent.websocket.sent[0]["event"]["type"] == "ticket.status_changed"


async def test_customer_only_receives_own_ticket_events() -> None:
    manager = ConnectionManager()
    org = uuid.uuid4()
    a_customer = await _connect(
        manager,
        org_id=org,
        user_id=uuid.uuid4(),
        email="alice@ex.test",
        role=UserRole.CUSTOMER,
    )
    b_customer = await _connect(
        manager,
        org_id=org,
        user_id=uuid.uuid4(),
        email="bob@ex.test",
        role=UserRole.CUSTOMER,
    )

    await manager.broadcast(
        RealtimeEvent(
            type=EventType.TICKET_STATUS_CHANGED,
            organization_id=org,
            ticket_id=uuid.uuid4(),
            ticket_customer_email="alice@ex.test",
        )
    )

    assert len(a_customer.websocket.sent) == 1
    assert len(b_customer.websocket.sent) == 0


async def test_notification_events_are_user_targeted() -> None:
    manager = ConnectionManager()
    org = uuid.uuid4()
    user_a_id = uuid.uuid4()
    user_b_id = uuid.uuid4()
    conn_a = await _connect(
        manager,
        org_id=org,
        user_id=user_a_id,
        email="a@ex.test",
        role=UserRole.AGENT,
    )
    conn_b = await _connect(
        manager,
        org_id=org,
        user_id=user_b_id,
        email="b@ex.test",
        role=UserRole.AGENT,
    )

    await manager.broadcast(
        RealtimeEvent(
            type=EventType.NOTIFICATION_CREATED,
            organization_id=org,
            target_user_id=user_a_id,
        )
    )

    assert len(conn_a.websocket.sent) == 1
    assert len(conn_b.websocket.sent) == 0


async def test_cross_tenant_isolation() -> None:
    manager = ConnectionManager()
    org_a = uuid.uuid4()
    org_b = uuid.uuid4()

    conn_a = await _connect(
        manager,
        org_id=org_a,
        user_id=uuid.uuid4(),
        email="a@ex.test",
        role=UserRole.ADMIN,
    )
    conn_b = await _connect(
        manager,
        org_id=org_b,
        user_id=uuid.uuid4(),
        email="b@ex.test",
        role=UserRole.ADMIN,
    )

    await manager.broadcast(
        RealtimeEvent(
            type=EventType.TICKET_STATUS_CHANGED,
            organization_id=org_a,
            ticket_id=uuid.uuid4(),
            ticket_customer_email="x@ex.test",
        )
    )

    assert len(conn_a.websocket.sent) == 1
    assert len(conn_b.websocket.sent) == 0


async def test_disconnect_removes_connection() -> None:
    manager = ConnectionManager()
    org = uuid.uuid4()
    conn = await _connect(
        manager,
        org_id=org,
        user_id=uuid.uuid4(),
        email="a@ex.test",
        role=UserRole.AGENT,
    )
    await manager.disconnect(conn)

    await manager.broadcast(
        RealtimeEvent(
            type=EventType.TICKET_STATUS_CHANGED,
            organization_id=org,
            ticket_id=uuid.uuid4(),
            ticket_customer_email="a@ex.test",
        )
    )
    assert len(conn.websocket.sent) == 0


async def test_wire_roundtrip_preserves_id() -> None:
    event = RealtimeEvent(
        type=EventType.TICKET_COMMENT_CREATED,
        organization_id=uuid.uuid4(),
        ticket_id=uuid.uuid4(),
        ticket_customer_email="c@ex.test",
        payload={"comment_id": "abc"},
    )
    wire = event.to_wire()
    parsed = RealtimeEvent.from_wire(wire)
    assert parsed.id == event.id
    assert parsed.type == event.type
    assert parsed.payload == event.payload