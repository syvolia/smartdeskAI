"""Cross-tenant and security-boundary tests.

These tests fail if any endpoint returns data belonging to an
organization other than the caller's. They are the load-bearing test
suite for the multi-tenancy invariant.
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models import (
    Customer,
    Notification,
    Organization,
    Ticket,
    TicketComment,
    TicketPriority,
    TicketStatus,
    User,
    UserRole,
)

pytestmark = pytest.mark.asyncio


async def _tenant(db: AsyncSession, *, slug: str):
    org = Organization(name=f"Org {slug}", slug=f"{slug}-{uuid.uuid4().hex[:6]}")
    db.add(org)
    await db.flush()

    admin = User(
        organization_id=org.id,
        email=f"admin-{slug}-{uuid.uuid4().hex[:4]}@ex.test",
        full_name="Admin",
        hashed_password=hash_password("TestPassw0rd!"),
        role=UserRole.ADMIN,
    )
    agent = User(
        organization_id=org.id,
        email=f"agent-{slug}-{uuid.uuid4().hex[:4]}@ex.test",
        full_name="Agent",
        hashed_password=hash_password("TestPassw0rd!"),
        role=UserRole.AGENT,
    )
    customer = Customer(
        organization_id=org.id,
        email=f"cust-{slug}-{uuid.uuid4().hex[:4]}@ex.test",
        full_name="Cust",
    )
    db.add_all([admin, agent, customer])
    await db.flush()

    ticket = Ticket(
        organization_id=org.id,
        customer_id=customer.id,
        assigned_agent_id=agent.id,
        title=f"{slug} ticket",
        description="…",
        status=TicketStatus.OPEN,
        priority=TicketPriority.MEDIUM,
    )
    db.add(ticket)
    await db.flush()

    comment = TicketComment(
        organization_id=org.id,
        ticket_id=ticket.id,
        author_user_id=agent.id,
        body="private comment",
    )
    db.add(comment)
    await db.flush()

    def header(u: User) -> dict:
        token, _ = create_access_token(u.id)
        return {"Authorization": f"Bearer {token}"}

    return {
        "org": org,
        "admin": admin, "admin_h": header(admin),
        "agent": agent, "agent_h": header(agent),
        "customer": customer,
        "ticket": ticket,
        "comment": comment,
    }


# ---------- ticket reads ----------


async def test_cannot_read_other_org_ticket(
    client: AsyncClient, db: AsyncSession
) -> None:
    a = await _tenant(db, slug="sec-a")
    b = await _tenant(db, slug="sec-b")

    r = await client.get(f"/api/v1/tickets/{b['ticket'].id}", headers=a["agent_h"])
    assert r.status_code == 404


async def test_cannot_read_other_org_comments(
    client: AsyncClient, db: AsyncSession
) -> None:
    a = await _tenant(db, slug="sec-a")
    b = await _tenant(db, slug="sec-b")

    r = await client.get(
        f"/api/v1/tickets/{b['ticket'].id}/comments", headers=a["agent_h"]
    )
    assert r.status_code == 404


async def test_cannot_read_other_org_events(
    client: AsyncClient, db: AsyncSession
) -> None:
    a = await _tenant(db, slug="sec-a")
    b = await _tenant(db, slug="sec-b")

    r = await client.get(
        f"/api/v1/tickets/{b['ticket'].id}/events", headers=a["agent_h"]
    )
    assert r.status_code == 404


# ---------- ticket writes ----------


async def test_cannot_update_other_org_ticket(
    client: AsyncClient, db: AsyncSession
) -> None:
    a = await _tenant(db, slug="sec-a")
    b = await _tenant(db, slug="sec-b")

    r = await client.patch(
        f"/api/v1/tickets/{b['ticket'].id}",
        json={"title": "hijacked"},
        headers=a["agent_h"],
    )
    assert r.status_code == 404


async def test_cannot_assign_other_org_ticket(
    client: AsyncClient, db: AsyncSession
) -> None:
    a = await _tenant(db, slug="sec-a")
    b = await _tenant(db, slug="sec-b")

    r = await client.post(
        f"/api/v1/tickets/{b['ticket'].id}/assign",
        json={"assigned_agent_id": str(a["agent"].id)},
        headers=a["admin_h"],
    )
    assert r.status_code == 404


async def test_cannot_comment_other_org_ticket(
    client: AsyncClient, db: AsyncSession
) -> None:
    a = await _tenant(db, slug="sec-a")
    b = await _tenant(db, slug="sec-b")

    r = await client.post(
        f"/api/v1/tickets/{b['ticket'].id}/comments",
        json={"body": "intrusion", "is_internal": False},
        headers=a["agent_h"],
    )
    assert r.status_code == 404


async def test_cannot_delete_other_org_ticket(
    client: AsyncClient, db: AsyncSession
) -> None:
    a = await _tenant(db, slug="sec-a")
    b = await _tenant(db, slug="sec-b")

    r = await client.delete(
        f"/api/v1/tickets/{b['ticket'].id}", headers=a["admin_h"]
    )
    assert r.status_code == 404


# ---------- list endpoints ----------


async def test_ticket_list_isolated(
    client: AsyncClient, db: AsyncSession
) -> None:
    a = await _tenant(db, slug="sec-a")
    b = await _tenant(db, slug="sec-b")

    r = await client.get("/api/v1/tickets", headers=a["agent_h"])
    ids = [t["id"] for t in r.json()["items"]]
    assert str(b["ticket"].id) not in ids


# ---------- notifications ----------


async def test_cannot_mark_other_users_notification_read(
    client: AsyncClient, db: AsyncSession
) -> None:
    a = await _tenant(db, slug="sec-a")
    b = await _tenant(db, slug="sec-b")

    notif = Notification(
        organization_id=b["org"].id,
        user_id=b["agent"].id,
        type="TICKET_ASSIGNED",
        title="B's notification",
        body="…",
    )
    db.add(notif)
    await db.flush()

    r = await client.patch(
        f"/api/v1/notifications/{notif.id}/read", headers=a["agent_h"]
    )
    assert r.status_code == 404


# ---------- analytics ----------


async def test_analytics_scoped_to_caller_org(
    client: AsyncClient, db: AsyncSession
) -> None:
    a = await _tenant(db, slug="sec-a")
    b = await _tenant(db, slug="sec-b")
    # Add 5 more tickets to B so the counts would differ if scoping failed.
    for i in range(5):
        db.add(
            Ticket(
                organization_id=b["org"].id,
                customer_id=b["customer"].id,
                title=f"extra-{i}",
                description="…",
                status=TicketStatus.OPEN,
                priority=TicketPriority.LOW,
            )
        )
    await db.flush()

    r = await client.get("/api/v1/analytics/dashboard", headers=a["admin_h"])
    assert r.status_code == 200
    # A has exactly 1 ticket, B has 6 — must see 1.
    assert r.json()["tickets"]["total"] == 1


# ---------- AI endpoints ----------


async def test_cannot_ai_classify_other_org_ticket(
    client: AsyncClient, db: AsyncSession
) -> None:
    a = await _tenant(db, slug="sec-a")
    b = await _tenant(db, slug="sec-b")

    r = await client.post(
        f"/api/v1/ai/tickets/{b['ticket'].id}/classify", headers=a["agent_h"]
    )
    assert r.status_code == 404


async def test_cannot_list_other_org_ai_suggestions(
    client: AsyncClient, db: AsyncSession
) -> None:
    a = await _tenant(db, slug="sec-a")
    b = await _tenant(db, slug="sec-b")

    r = await client.get(
        f"/api/v1/ai/tickets/{b['ticket'].id}/suggestions", headers=a["agent_h"]
    )
    assert r.status_code == 404


# ---------- admin ----------


async def test_agent_cannot_reach_admin_endpoints(
    client: AsyncClient, db: AsyncSession
) -> None:
    a = await _tenant(db, slug="sec-a")
    paths = [
        "/api/v1/admin/overview",
        "/api/v1/admin/organization",
        "/api/v1/admin/users",
        "/api/v1/admin/ai-config",
    ]
    for path in paths:
        r = await client.get(path, headers=a["agent_h"])
        assert r.status_code == 403, f"{path} returned {r.status_code}"


# ---------- auth edge cases ----------


async def test_me_with_tampered_token_rejected(
    client: AsyncClient, db: AsyncSession
) -> None:
    a = await _tenant(db, slug="sec-a")
    r = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {a['admin_h']['Authorization'][7:]}tampered"},
    )
    assert r.status_code == 401


async def test_no_client_supplied_org_id_is_honoured(
    client: AsyncClient, db: AsyncSession
) -> None:
    """Even if a client sends org_id in the body or header, the server
    must use the token-derived org."""
    a = await _tenant(db, slug="sec-a")
    b = await _tenant(db, slug="sec-b")

    r = await client.post(
        "/api/v1/tickets",
        json={
            "title": "x",
            "description": "y",
            "customer_id": str(a["customer"].id),
            "organization_id": str(b["org"].id),  # ignored — not in schema
        },
        headers={
            **a["admin_h"],
            "X-Organization-Id": str(b["org"].id),  # ignored — not read
        },
    )
    assert r.status_code == 201
    assert r.json()["organization_id"] == str(a["org"].id)


# ---------- rate limiting ----------


async def test_login_is_rate_limited(
    client: AsyncClient, db: AsyncSession, mock_redis
) -> None:
    """Hammer /login and confirm 429 after the limit."""
    from app.db.redis import get_redis
    from app.main import app as fastapi_app

    fastapi_app.dependency_overrides[get_redis] = lambda: mock_redis
    try:
        statuses = []
        for _ in range(15):
            r = await client.post(
                "/api/v1/auth/login",
                json={"email": "nobody@ex.test", "password": "whatever"},
            )
            statuses.append(r.status_code)
        assert 429 in statuses, f"Never rate limited: {statuses}"
    finally:
        fastapi_app.dependency_overrides.clear()


# ---------- file upload ----------


async def test_reject_executable_upload(
    client: AsyncClient, db: AsyncSession
) -> None:
    a = await _tenant(db, slug="sec-a")
    r = await client.post(
        f"/api/v1/tickets/{a['ticket'].id}/attachments",
        files={"file": ("evil.sh", b"#!/bin/sh\nrm -rf /", "application/x-sh")},
        headers=a["agent_h"],
    )
    assert r.status_code == 422


async def test_reject_disguised_content(
    client: AsyncClient, db: AsyncSession
) -> None:
    """A file claiming to be PNG but whose bytes are not PNG must fail."""
    a = await _tenant(db, slug="sec-a")
    r = await client.post(
        f"/api/v1/tickets/{a['ticket'].id}/attachments",
        files={"file": ("logo.png", b"<?php system($_GET['x']); ?>", "image/png")},
        headers=a["agent_h"],
    )
    assert r.status_code == 422


async def test_accept_valid_png(
    client: AsyncClient, db: AsyncSession
) -> None:
    a = await _tenant(db, slug="sec-a")
    png_header = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
    r = await client.post(
        f"/api/v1/tickets/{a['ticket'].id}/attachments",
        files={"file": ("logo.png", png_header, "image/png")},
        headers=a["agent_h"],
    )
    assert r.status_code == 201, r.text