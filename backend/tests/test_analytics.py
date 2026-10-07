"""Analytics endpoint tests.

Verifies the aggregate values against hand-built fixtures. No AI calls,
no network, no external services.
"""

from datetime import date, datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models import (
    AIJob,
    AIJobStatus,
    AIOperation,
    AISuggestion,
    AISuggestionKind,
    AISuggestionStatus,
    Customer,
    Organization,
    Ticket,
    TicketPriority,
    TicketStatus,
    User,
    UserRole,
)
from app.core.security import hash_password

pytestmark = pytest.mark.asyncio


async def _setup(db: AsyncSession):
    org = Organization(name="Acme", slug=f"acme-{datetime.now().timestamp()}")
    db.add(org)
    await db.flush()

    admin = User(
        organization_id=org.id,
        email=f"admin-{org.id.hex[:6]}@ex.test",
        full_name="Ada Admin",
        hashed_password=hash_password("pw"),
        role=UserRole.ADMIN,
    )
    agent1 = User(
        organization_id=org.id,
        email=f"agent1-{org.id.hex[:6]}@ex.test",
        full_name="Grace Agent",
        hashed_password=hash_password("pw"),
        role=UserRole.AGENT,
    )
    agent2 = User(
        organization_id=org.id,
        email=f"agent2-{org.id.hex[:6]}@ex.test",
        full_name="Linus Agent",
        hashed_password=hash_password("pw"),
        role=UserRole.AGENT,
    )
    customer = Customer(
        organization_id=org.id,
        email=f"c-{org.id.hex[:6]}@ex.test",
        full_name="Cust",
    )
    db.add_all([admin, agent1, agent2, customer])
    await db.flush()

    # Six tickets across statuses/priorities/agents with known timestamps.
    now = datetime.now(timezone.utc)
    rows = [
        # (status, priority, agent_id, created_days_ago, resolved_days_ago, breached)
        (TicketStatus.OPEN, TicketPriority.HIGH, agent1.id, 1, None, False),
        (TicketStatus.IN_PROGRESS, TicketPriority.URGENT, agent1.id, 2, None, True),
        (TicketStatus.WAITING_CUSTOMER, TicketPriority.MEDIUM, agent2.id, 3, None, False),
        (TicketStatus.RESOLVED, TicketPriority.LOW, agent1.id, 5, 2, False),
        (TicketStatus.RESOLVED, TicketPriority.HIGH, agent2.id, 8, 3, False),
        (TicketStatus.CLOSED, TicketPriority.MEDIUM, agent2.id, 10, 4, True),
    ]
    for status, priority, agent_id, created_days, resolved_days, breached in rows:
        created_at = now - timedelta(days=created_days)
        resolved_at = now - timedelta(days=resolved_days) if resolved_days else None
        first_response_at = (
            created_at + timedelta(hours=2) if status not in (TicketStatus.OPEN,) else None
        )
        db.add(
            Ticket(
                organization_id=org.id,
                customer_id=customer.id,
                assigned_agent_id=agent_id,
                title=f"Ticket {status.value}",
                description="...",
                status=status,
                priority=priority,
                created_at=created_at,
                resolved_at=resolved_at,
                first_response_at=first_response_at,
                sla_breached=breached,
            )
        )
    await db.flush()

    # AI suggestions: 3 accepted, 1 rejected, 1 pending across 2 kinds.
    for kind, status in [
        (AISuggestionKind.CLASSIFICATION, AISuggestionStatus.ACCEPTED),
        (AISuggestionKind.CLASSIFICATION, AISuggestionStatus.ACCEPTED),
        (AISuggestionKind.PRIORITY, AISuggestionStatus.ACCEPTED),
        (AISuggestionKind.PRIORITY, AISuggestionStatus.REJECTED),
        (AISuggestionKind.SUMMARY, AISuggestionStatus.PENDING),
    ]:
        ticket_id = (
            await db.scalar(
                Ticket.__table__.select().with_only_columns(Ticket.id).limit(1)
            )
        )
        db.add(
            AISuggestion(
                organization_id=org.id,
                ticket_id=ticket_id,
                kind=kind,
                status=status,
                payload={"k": "v"},
                confidence=0.85 if kind == AISuggestionKind.CLASSIFICATION else 0.55,
                model="mock-model",
            )
        )
    await db.flush()

    token, _ = create_access_token(admin.id)
    return org, admin, {"Authorization": f"Bearer {token}"}


async def test_dashboard_overview(
    client: AsyncClient, db: AsyncSession
) -> None:
    _org, _admin, headers = await _setup(db)

    r = await client.get("/api/v1/analytics/dashboard", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()

    tickets = body["tickets"]
    assert tickets["total"] == 6
    assert tickets["open"] == 1
    assert tickets["in_progress"] == 1
    assert tickets["waiting_customer"] == 1
    assert tickets["resolved"] == 2
    assert tickets["closed"] == 1

    priorities = {row["name"]: row["value"] for row in tickets["by_priority"]}
    assert priorities["HIGH"] == 2
    assert priorities["URGENT"] == 1


async def test_dashboard_sla(
    client: AsyncClient, db: AsyncSession
) -> None:
    _org, _admin, headers = await _setup(db)

    r = await client.get("/api/v1/analytics/dashboard", headers=headers)
    sla = r.json()["sla"]

    # 2 breaches out of 6 tickets = 66.67% compliance
    assert sla["breached"] == 2
    assert sla["total_with_sla"] == 6
    assert sla["sla_compliance_percentage"] == pytest.approx(66.67, abs=0.1)

    # First response avg = 2 hours for tickets that have it (5 tickets)
    assert sla["first_response_samples"] == 5
    assert sla["first_response_avg_seconds"] == pytest.approx(7200, abs=1)


async def test_dashboard_agent_workload(
    client: AsyncClient, db: AsyncSession
) -> None:
    _org, _admin, headers = await _setup(db)

    r = await client.get("/api/v1/analytics/dashboard", headers=headers)
    agents = {row["agent_name"]: row for row in r.json()["agents"]}
    # Two agents present.
    assert "Grace Agent" in agents
    assert "Linus Agent" in agents
    # Grace: tickets 1, 2, 4 → open=1, in_progress=1, resolved=1, total=3
    assert agents["Grace Agent"]["total_assigned"] == 3
    assert agents["Grace Agent"]["open_tickets"] == 1
    assert agents["Grace Agent"]["in_progress_tickets"] == 1
    assert agents["Grace Agent"]["resolved_tickets"] == 1
    # Linus: tickets 3, 5, 6 → waiting=1, resolved=1, closed=1, total=3
    assert agents["Linus Agent"]["total_assigned"] == 3
    assert agents["Linus Agent"]["waiting_customer_tickets"] == 1
    assert agents["Linus Agent"]["closed_tickets"] == 1


async def test_dashboard_ai_metrics(
    client: AsyncClient, db: AsyncSession
) -> None:
    _org, _admin, headers = await _setup(db)

    r = await client.get("/api/v1/analytics/dashboard", headers=headers)
    ai = r.json()["ai"]["overall"]

    assert ai["suggestions_generated"] == 5
    assert ai["suggestions_accepted"] == 3
    assert ai["suggestions_rejected"] == 1
    assert ai["suggestions_pending"] == 1
    # 3 accepted / (3 + 1) = 75%
    assert ai["acceptance_rate"] == pytest.approx(75.0, abs=0.1)


async def test_dashboard_confidence_distribution(
    client: AsyncClient, db: AsyncSession
) -> None:
    _org, _admin, headers = await _setup(db)

    r = await client.get("/api/v1/analytics/dashboard", headers=headers)
    buckets = {b["bucket"]: b["count"] for b in r.json()["ai"]["confidence_distribution"]}
    # Two suggestions at 0.85 → bucket 0.8-1.0; three at 0.55 → bucket 0.4-0.6.
    assert buckets["0.8-1.0"] == 2
    assert buckets["0.4-0.6"] == 3


async def test_dashboard_cross_tenant_isolation(
    client: AsyncClient, db: AsyncSession
) -> None:
    """Analytics must never include another org's tickets."""
    _org_a, _admin_a, headers_a = await _setup(db)
    _org_b, _admin_b, _headers_b = await _setup(db)

    r = await client.get("/api/v1/analytics/dashboard", headers=headers_a)
    assert r.status_code == 200
    # Should only see org A's six tickets.
    assert r.json()["tickets"]["total"] == 6


async def test_dashboard_requires_staff(
    client: AsyncClient, db: AsyncSession
) -> None:
    org, _admin, _headers = await _setup(db)
    cust_user = User(
        organization_id=org.id,
        email=f"cust-user-{org.id.hex[:6]}@ex.test",
        full_name="Cust",
        hashed_password=hash_password("pw"),
        role=UserRole.CUSTOMER,
    )
    db.add(cust_user)
    await db.flush()
    token, _ = create_access_token(cust_user.id)

    r = await client.get(
        "/api/v1/analytics/dashboard",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


async def test_dashboard_date_filter(
    client: AsyncClient, db: AsyncSession
) -> None:
    _org, _admin, headers = await _setup(db)

    today = date.today()
    # Only include tickets created in the last 2 days.
    r = await client.get(
        "/api/v1/analytics/dashboard",
        params={
            "date_from": (today - timedelta(days=2)).isoformat(),
            "date_to": today.isoformat(),
        },
        headers=headers,
    )
    assert r.status_code == 200
    # Tickets created 1 and 2 days ago only (2 total).
    assert r.json()["tickets"]["total"] == 2