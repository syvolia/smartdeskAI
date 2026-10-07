"""Admin area tests.

The most important assertions here are the role guards: every admin
endpoint must reject non-admins on the *server*, regardless of what the
frontend shows.
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models import (
    NotificationPreference,
    Organization,
    SLA,
    Team,
    TicketCategory,
    User,
    UserRole,
)

pytestmark = pytest.mark.asyncio


async def _tenant(db: AsyncSession, *, slug: str):
    org = Organization(name="Admin Test", slug=slug)
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
    customer = User(
        organization_id=org.id,
        email=f"cust-{slug}@ex.test",
        full_name="Cust One",
        hashed_password=hash_password("pw"),
        role=UserRole.CUSTOMER,
    )
    db.add_all([admin, agent, customer])
    await db.flush()

    def header(user: User) -> dict[str, str]:
        token, _ = create_access_token(user.id)
        return {"Authorization": f"Bearer {token}"}

    return {
        "org": org,
        "admin": admin,
        "agent": agent,
        "customer": customer,
        "admin_h": header(admin),
        "agent_h": header(agent),
        "customer_h": header(customer),
    }


# ---------- overview ----------


async def test_overview_admin_ok(client: AsyncClient, db: AsyncSession) -> None:
    ctx = await _tenant(db, slug="ov-admin")
    r = await client.get("/api/v1/admin/overview", headers=ctx["admin_h"])
    assert r.status_code == 200
    body = r.json()
    assert body["users"] == 3
    assert body["plan"] == "free"


async def test_overview_agent_forbidden(
    client: AsyncClient, db: AsyncSession
) -> None:
    ctx = await _tenant(db, slug="ov-agent")
    r = await client.get("/api/v1/admin/overview", headers=ctx["agent_h"])
    assert r.status_code == 403


async def test_overview_customer_forbidden(
    client: AsyncClient, db: AsyncSession
) -> None:
    ctx = await _tenant(db, slug="ov-cust")
    r = await client.get("/api/v1/admin/overview", headers=ctx["customer_h"])
    assert r.status_code == 403


async def test_overview_unauthenticated(client: AsyncClient) -> None:
    r = await client.get("/api/v1/admin/overview")
    assert r.status_code == 401


# ---------- organization ----------


async def test_org_profile_update(
    client: AsyncClient, db: AsyncSession
) -> None:
    ctx = await _tenant(db, slug="org-update")
    r = await client.patch(
        "/api/v1/admin/organization",
        json={"name": "New Name", "settings": {"timezone": "UTC"}},
        headers=ctx["admin_h"],
    )
    assert r.status_code == 200
    assert r.json()["name"] == "New Name"
    assert r.json()["settings"]["timezone"] == "UTC"


async def test_org_update_agent_forbidden(
    client: AsyncClient, db: AsyncSession
) -> None:
    ctx = await _tenant(db, slug="org-agent")
    r = await client.patch(
        "/api/v1/admin/organization",
        json={"name": "Hijack"},
        headers=ctx["agent_h"],
    )
    assert r.status_code == 403


# ---------- users ----------


async def test_create_user(
    client: AsyncClient, db: AsyncSession
) -> None:
    ctx = await _tenant(db, slug="user-create")
    r = await client.post(
        "/api/v1/admin/users",
        json={
            "email": "new-agent@ex.test",
            "full_name": "New Agent",
            "role": "AGENT",
            "password": "TestPass123!",
        },
        headers=ctx["admin_h"],
    )
    assert r.status_code == 201
    assert r.json()["role"] == "AGENT"


async def test_create_user_agent_forbidden(
    client: AsyncClient, db: AsyncSession
) -> None:
    ctx = await _tenant(db, slug="user-agent")
    r = await client.post(
        "/api/v1/admin/users",
        json={
            "email": "x@ex.test",
            "full_name": "X",
            "role": "AGENT",
            "password": "TestPass123!",
        },
        headers=ctx["agent_h"],
    )
    assert r.status_code == 403


async def test_cannot_demote_self(
    client: AsyncClient, db: AsyncSession
) -> None:
    ctx = await _tenant(db, slug="self-demote")
    r = await client.patch(
        f"/api/v1/admin/users/{ctx['admin'].id}",
        json={"role": "AGENT"},
        headers=ctx["admin_h"],
    )
    assert r.status_code == 422


async def test_cannot_deactivate_self(
    client: AsyncClient, db: AsyncSession
) -> None:
    ctx = await _tenant(db, slug="self-deactivate")
    r = await client.patch(
        f"/api/v1/admin/users/{ctx['admin'].id}",
        json={"is_active": False},
        headers=ctx["admin_h"],
    )
    assert r.status_code == 422


# ---------- teams ----------


async def test_create_team(client: AsyncClient, db: AsyncSession) -> None:
    ctx = await _tenant(db, slug="team-create")
    r = await client.post(
        "/api/v1/admin/teams",
        json={"name": "Tier 2"},
        headers=ctx["admin_h"],
    )
    assert r.status_code == 201
    assert r.json()["name"] == "Tier 2"


async def test_list_teams_agent_ok(
    client: AsyncClient, db: AsyncSession
) -> None:
    ctx = await _tenant(db, slug="team-read-agent")
    r = await client.get("/api/v1/admin/teams", headers=ctx["agent_h"])
    assert r.status_code == 200


async def test_create_team_agent_forbidden(
    client: AsyncClient, db: AsyncSession
) -> None:
    ctx = await _tenant(db, slug="team-write-agent")
    r = await client.post(
        "/api/v1/admin/teams",
        json={"name": "Illegal"},
        headers=ctx["agent_h"],
    )
    assert r.status_code == 403


# ---------- ticket categories ----------


async def test_category_crud(client: AsyncClient, db: AsyncSession) -> None:
    ctx = await _tenant(db, slug="cat-crud")

    r = await client.post(
        "/api/v1/admin/ticket-categories",
        json={"name": "Billing"},
        headers=ctx["admin_h"],
    )
    assert r.status_code == 201
    cat_id = r.json()["id"]

    r = await client.patch(
        f"/api/v1/admin/ticket-categories/{cat_id}",
        json={"description": "Invoices and payments"},
        headers=ctx["admin_h"],
    )
    assert r.status_code == 200

    r = await client.delete(
        f"/api/v1/admin/ticket-categories/{cat_id}", headers=ctx["admin_h"]
    )
    assert r.status_code == 204


async def test_category_agent_cannot_write(
    client: AsyncClient, db: AsyncSession
) -> None:
    ctx = await _tenant(db, slug="cat-agent")
    r = await client.post(
        "/api/v1/admin/ticket-categories",
        json={"name": "X"},
        headers=ctx["agent_h"],
    )
    assert r.status_code == 403


# ---------- SLAs ----------


async def test_sla_crud(client: AsyncClient, db: AsyncSession) -> None:
    ctx = await _tenant(db, slug="sla-crud")

    r = await client.post(
        "/api/v1/admin/slas",
        json={
            "name": "Standard",
            "priority": "MEDIUM",
            "first_response_minutes": 60,
            "resolution_minutes": 480,
        },
        headers=ctx["admin_h"],
    )
    assert r.status_code == 201
    sla_id = r.json()["id"]

    r = await client.patch(
        f"/api/v1/admin/slas/{sla_id}",
        json={"resolution_minutes": 240},
        headers=ctx["admin_h"],
    )
    assert r.status_code == 200
    assert r.json()["resolution_minutes"] == 240

    r = await client.delete(
        f"/api/v1/admin/slas/{sla_id}", headers=ctx["admin_h"]
    )
    assert r.status_code == 204


# ---------- AI config ----------


async def test_ai_config_roundtrip(
    client: AsyncClient, db: AsyncSession
) -> None:
    ctx = await _tenant(db, slug="ai-config")
    r = await client.get("/api/v1/admin/ai-config", headers=ctx["admin_h"])
    assert r.status_code == 200
    assert r.json()["enabled"] is False

    r = await client.patch(
        "/api/v1/admin/ai-config",
        json={"ai_config": {"enabled": True, "min_confidence": 0.75}},
        headers=ctx["admin_h"],
    )
    assert r.status_code == 200
    assert r.json()["ai_config"]["enabled"] is True
    assert r.json()["ai_config"]["min_confidence"] == 0.75


async def test_ai_config_agent_forbidden(
    client: AsyncClient, db: AsyncSession
) -> None:
    ctx = await _tenant(db, slug="ai-agent")
    r = await client.get("/api/v1/admin/ai-config", headers=ctx["agent_h"])
    assert r.status_code == 403


# ---------- notification preferences ----------


async def test_notification_prefs_self(
    client: AsyncClient, db: AsyncSession
) -> None:
    ctx = await _tenant(db, slug="notif-self")

    r = await client.get(
        "/api/v1/admin/notification-preferences/me", headers=ctx["agent_h"]
    )
    assert r.status_code == 200

    r = await client.put(
        "/api/v1/admin/notification-preferences/me",
        json={"prefs": {"SLA_BREACHED": {"email": False, "in_app": True}}},
        headers=ctx["agent_h"],
    )
    assert r.status_code == 200
    assert r.json()["prefs"]["SLA_BREACHED"]["email"] is False


async def test_notification_prefs_agent_cannot_read_other(
    client: AsyncClient, db: AsyncSession
) -> None:
    ctx = await _tenant(db, slug="notif-agent-other")
    r = await client.get(
        f"/api/v1/admin/notification-preferences/{ctx['admin'].id}",
        headers=ctx["agent_h"],
    )
    assert r.status_code == 403


async def test_notification_prefs_admin_can_read_other(
    client: AsyncClient, db: AsyncSession
) -> None:
    ctx = await _tenant(db, slug="notif-admin-other")
    r = await client.get(
        f"/api/v1/admin/notification-preferences/{ctx['agent'].id}",
        headers=ctx["admin_h"],
    )
    assert r.status_code == 200


# ---------- tenant isolation on admin routes ----------


async def test_tenant_isolation_users(
    client: AsyncClient, db: AsyncSession
) -> None:
    ctx_a = await _tenant(db, slug="iso-a")
    ctx_b = await _tenant(db, slug="iso-b")

    # A's admin lists users — must only see A's.
    r = await client.get("/api/v1/admin/users", headers=ctx_a["admin_h"])
    emails = [u["email"] for u in r.json()["items"]]
    assert all(email.endswith("-iso-a@ex.test") for email in emails)


async def test_tenant_isolation_org_update(
    client: AsyncClient, db: AsyncSession
) -> None:
    ctx_a = await _tenant(db, slug="iso-org-a")
    ctx_b = await _tenant(db, slug="iso-org-b")

    await client.patch(
        "/api/v1/admin/organization",
        json={"name": "B Renamed"},
        headers=ctx_b["admin_h"],
    )

    # A's org is untouched.
    r = await client.get("/api/v1/admin/organization", headers=ctx_a["admin_h"])
    assert r.json()["name"] != "B Renamed"