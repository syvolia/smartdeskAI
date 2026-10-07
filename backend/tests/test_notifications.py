"""Notification dispatch, endpoints, and tenant isolation."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models import (
    Customer,
    Notification,
    NotificationType,
    Organization,
    Ticket,
    TicketPriority,
    TicketStatus,
    User,
    UserRole,
)
from app.notifications.base import NotificationMessage
from app.notifications.service import NotificationService

pytestmark = pytest.mark.asyncio


async def _setup(db: AsyncSession, *, slug: str = "notif-test"):
    org = Organization(name="Notif Test", slug=f"{slug}-{id(db)}")
    db.add(org)
    await db.flush()

    admin = User(
        organization_id=org.id,
        email=f"admin-{slug}@ex.test",
        full_name="Ada Admin",
        hashed_password=hash_password("pw"),
        role=UserRole.ADMIN,
    )
    agent = User(
        organization_id=org.id,
        email=f"agent-{slug}@ex.test",
        full_name="Grace Agent",
        hashed_password=hash_password("pw"),
        role=UserRole.AGENT,
    )
    customer = Customer(
        organization_id=org.id,
        email=f"cust-{slug}@ex.test",
        full_name="Cust",
    )
    db.add_all([admin, agent, customer])
    await db.flush()

    ticket = Ticket(
        organization_id=org.id,
        customer_id=customer.id,
        assigned_agent_id=agent.id,
        title="Test ticket",
        description="...",
        status=TicketStatus.OPEN,
        priority=TicketPriority.MEDIUM,
    )
    db.add(ticket)
    await db.flush()

    admin_token, _ = create_access_token(admin.id)
    agent_token, _ = create_access_token(agent.id)
    return {
        "org": org,
        "admin": admin,
        "agent": agent,
        "customer": customer,
        "ticket": ticket,
        "admin_headers": {"Authorization": f"Bearer {admin_token}"},
        "agent_headers": {"Authorization": f"Bearer {agent_token}"},
    }


# ---------- endpoints ----------


async def test_list_notifications_empty(
    client: AsyncClient, db: AsyncSession
) -> None:
    ctx = await _setup(db)
    r = await client.get("/api/v1/notifications", headers=ctx["agent_headers"])
    assert r.status_code == 200
    body = r.json()
    assert body["items"] == []
    assert body["unread_count"] == 0


async def test_mark_read_and_unread_count(
    client: AsyncClient, db: AsyncSession
) -> None:
    ctx = await _setup(db)
    db.add(
        Notification(
            organization_id=ctx["org"].id,
            user_id=ctx["agent"].id,
            type=NotificationType.TICKET_ASSIGNED,
            title="You got a ticket",
            body="…",
        )
    )
    await db.flush()

    r = await client.get("/api/v1/notifications", headers=ctx["agent_headers"])
    assert r.json()["unread_count"] == 1
    nid = r.json()["items"][0]["id"]

    r = await client.patch(
        f"/api/v1/notifications/{nid}/read", headers=ctx["agent_headers"]
    )
    assert r.status_code == 200
    assert r.json()["notification"]["read_at"] is not None

    r = await client.get("/api/v1/notifications", headers=ctx["agent_headers"])
    assert r.json()["unread_count"] == 0


async def test_mark_all_read(
    client: AsyncClient, db: AsyncSession
) -> None:
    ctx = await _setup(db)
    for i in range(3):
        db.add(
            Notification(
                organization_id=ctx["org"].id,
                user_id=ctx["agent"].id,
                type=NotificationType.TICKET_COMMENT,
                title=f"Comment {i}",
                body="…",
            )
        )
    await db.flush()

    r = await client.patch(
        "/api/v1/notifications/read-all", headers=ctx["agent_headers"]
    )
    assert r.status_code == 200
    assert r.json()["updated"] == 3

    r = await client.get("/api/v1/notifications", headers=ctx["agent_headers"])
    assert r.json()["unread_count"] == 0


async def test_mark_read_wrong_user_404(
    client: AsyncClient, db: AsyncSession
) -> None:
    """An agent cannot mark another user's notification as read."""
    ctx = await _setup(db)
    n = Notification(
        organization_id=ctx["org"].id,
        user_id=ctx["admin"].id,
        type=NotificationType.TICKET_ASSIGNED,
        title="Admin notification",
        body="…",
    )
    db.add(n)
    await db.flush()

    r = await client.patch(
        f"/api/v1/notifications/{n.id}/read",
        headers=ctx["agent_headers"],
    )
    assert r.status_code == 404


async def test_cross_tenant_isolation(
    client: AsyncClient, db: AsyncSession
) -> None:
    ctx_a = await _setup(db, slug="tenant-a")
    ctx_b = await _setup(db, slug="tenant-b")

    # Create a notification for B's agent.
    db.add(
        Notification(
            organization_id=ctx_b["org"].id,
            user_id=ctx_b["agent"].id,
            type=NotificationType.TICKET_ASSIGNED,
            title="B's notification",
            body="…",
        )
    )
    await db.flush()

    # A's agent lists their own — must not see B's.
    r = await client.get(
        "/api/v1/notifications", headers=ctx_a["agent_headers"]
    )
    assert r.status_code == 200
    assert r.json()["items"] == []


async def test_unauthenticated_401(client: AsyncClient) -> None:
    r = await client.get("/api/v1/notifications")
    assert r.status_code == 401


# ---------- service dispatch + dedupe ----------


async def test_dedupe_prevents_duplicate_delivery(
    db: AsyncSession, mock_redis
) -> None:
    """Two dispatches with the same dedupe key produce one notification."""
    from app.notifications.channels.in_app import InAppChannel

    ctx = await _setup(db, slug="dedupe-test")
    channel = InAppChannel(db=db, redis=mock_redis)
    service = NotificationService(db=db, redis=mock_redis, channels=[channel])

    message = NotificationMessage(
        organization_id=ctx["org"].id,
        user_id=ctx["agent"].id,
        type=NotificationType.TICKET_ASSIGNED,
        title="hi",
        body="…",
        entity_type="ticket",
        entity_id=ctx["ticket"].id,
        dedupe_key=f"assign:{ctx['ticket'].id}:{ctx['agent'].id}",
    )

    await service.dispatch([message])
    await service.dispatch([message])

    rows = list(
        (
            await db.scalars(
                select(Notification).where(
                    Notification.user_id == ctx["agent"].id,
                    Notification.title == "hi",
                )
            )
        ).all()
    )
    assert len(rows) == 1


async def test_dedupe_key_allows_second_delivery_for_different_key(
    db: AsyncSession, mock_redis
) -> None:
    from app.notifications.channels.in_app import InAppChannel

    ctx = await _setup(db, slug="dedupe2-test")
    channel = InAppChannel(db=db, redis=mock_redis)
    service = NotificationService(db=db, redis=mock_redis, channels=[channel])

    m1 = NotificationMessage(
        organization_id=ctx["org"].id,
        user_id=ctx["agent"].id,
        type=NotificationType.TICKET_ASSIGNED,
        title="first",
        body="…",
        dedupe_key="k1",
    )
    m2 = NotificationMessage(
        organization_id=ctx["org"].id,
        user_id=ctx["agent"].id,
        type=NotificationType.TICKET_ASSIGNED,
        title="second",
        body="…",
        dedupe_key="k2",
    )
    await service.dispatch([m1])
    await service.dispatch([m2])

    count = int(
        await db.scalar(
            select(Notification).where(Notification.user_id == ctx["agent"].id).with_only_columns(Notification.id).count()
        ) if False else 0
    )
    # Explicit count using ORM
    from sqlalchemy import func

    count = int(
        await db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == ctx["agent"].id)
        )
        or 0
    )
    assert count == 2


# ---------- end-to-end via ticket actions ----------


async def test_assign_triggers_notification(
    client: AsyncClient, db: AsyncSession, mock_redis
) -> None:
    """Assigning a ticket produces a TICKET_ASSIGNED notification for the
    new assignee."""
    from app.db.redis import get_redis
    from app.notifications.factory import get_notification_service
    from app.main import app as fastapi_app

    ctx = await _setup(db, slug="assign-notif")

    async def override_db():
        yield db

    def override_notif():
        from app.notifications.channels.in_app import InAppChannel

        channel = InAppChannel(db=db, redis=mock_redis)
        return NotificationService(db=db, redis=mock_redis, channels=[channel])

    fastapi_app.dependency_overrides[get_redis] = lambda: mock_redis
    fastapi_app.dependency_overrides[get_notification_service] = override_notif
    try:
        r = await client.post(
            f"/api/v1/tickets/{ctx['ticket'].id}/assign",
            json={"assigned_agent_id": str(ctx["agent"].id)},
            headers=ctx["admin_headers"],
        )
        assert r.status_code == 200

        rows = list(
            (
                await db.scalars(
                    select(Notification).where(
                        Notification.user_id == ctx["agent"].id,
                        Notification.type == NotificationType.TICKET_ASSIGNED,
                    )
                )
            ).all()
        )
        assert len(rows) == 1
    finally:
        fastapi_app.dependency_overrides.clear()