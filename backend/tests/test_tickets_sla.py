"""SLA deadline, first-response, and breach tests."""

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from app.models import SLA, TicketPriority, UserRole
from tests.helpers import authed_user, create_ticket

pytestmark = pytest.mark.asyncio


async def _seed_sla(db, org):
    db.add(
        SLA(
            organization_id=org.id,
            name="Standard",
            priority=TicketPriority.MEDIUM,
            first_response_minutes=60,
            resolution_minutes=480,
        )
    )
    await db.flush()


async def test_first_response_set_on_first_staff_comment(
    client: AsyncClient, db, make_org, make_user, make_customer
) -> None:
    org, _, headers = await authed_user(make_org, make_user, UserRole.AGENT)
    await _seed_sla(db, org)
    customer = await make_customer(org=org)
    ticket = await create_ticket(client, headers, customer_id=customer.id)

    assert ticket["sla"]["first_response_at"] is None

    await client.post(
        f"/api/v1/tickets/{ticket['id']}/comments",
        json={"body": "hi there", "is_internal": False},
        headers=headers,
    )

    r = await client.get(f"/api/v1/tickets/{ticket['id']}", headers=headers)
    assert r.json()["sla"]["first_response_at"] is not None
    assert r.json()["sla"]["first_response_time_seconds"] is not None


async def test_internal_note_does_not_set_first_response(
    client: AsyncClient, db, make_org, make_user, make_customer
) -> None:
    org, _, headers = await authed_user(make_org, make_user, UserRole.AGENT)
    await _seed_sla(db, org)
    customer = await make_customer(org=org)
    ticket = await create_ticket(client, headers, customer_id=customer.id)

    await client.post(
        f"/api/v1/tickets/{ticket['id']}/comments",
        json={"body": "psst", "is_internal": True},
        headers=headers,
    )
    r = await client.get(f"/api/v1/tickets/{ticket['id']}", headers=headers)
    assert r.json()["sla"]["first_response_at"] is None


async def test_breached_flag_false_before_deadline(
    client: AsyncClient, db, make_org, make_user, make_customer
) -> None:
    org, _, headers = await authed_user(make_org, make_user, UserRole.AGENT)
    await _seed_sla(db, org)
    customer = await make_customer(org=org)
    ticket = await create_ticket(client, headers, customer_id=customer.id)

    assert ticket["sla"]["first_response_breached"] is False
    assert ticket["sla"]["resolution_breached"] is False
    assert ticket["sla"]["sla_breached"] is False


async def test_response_breach_when_past_due(
    client: AsyncClient, db, make_org, make_user, make_customer
) -> None:
    """Backdate the ticket and verify breach is reported."""
    from sqlalchemy import select

    from app.models import Ticket

    org, _, headers = await authed_user(make_org, make_user, UserRole.AGENT)
    await _seed_sla(db, org)
    customer = await make_customer(org=org)
    ticket = await create_ticket(client, headers, customer_id=customer.id)

    # Backdate created_at to 3 hours ago so the response deadline is in the past.
    db_ticket = await db.scalar(select(Ticket).where(Ticket.id == ticket["id"]))
    past = datetime.now(timezone.utc) - timedelta(hours=3)
    db_ticket.created_at = past
    db_ticket.first_response_due_at = past + timedelta(minutes=60)
    db_ticket.resolution_due_at = past + timedelta(minutes=480)
    await db.flush()

    r = await client.get(f"/api/v1/tickets/{ticket['id']}", headers=headers)
    sla = r.json()["sla"]
    assert sla["first_response_breached"] is True
    assert sla["sla_breached"] is True


async def test_resolution_breach_when_resolved_late(
    client: AsyncClient, db, make_org, make_user, make_customer
) -> None:
    from sqlalchemy import select

    from app.models import Ticket

    org, _, headers = await authed_user(make_org, make_user, UserRole.AGENT)
    await _seed_sla(db, org)
    customer = await make_customer(org=org)
    ticket = await create_ticket(client, headers, customer_id=customer.id)

    db_ticket = await db.scalar(select(Ticket).where(Ticket.id == ticket["id"]))
    past = datetime.now(timezone.utc) - timedelta(hours=3)
    db_ticket.created_at = past
    db_ticket.first_response_due_at = past + timedelta(minutes=60)
    db_ticket.resolution_due_at = past + timedelta(minutes=480)
    await db.flush()

    # Resolve now (well past 480 min from 3h ago? no, we're within window).
    # Set resolution_due_at further back to force a breach.
    db_ticket.resolution_due_at = past + timedelta(minutes=30)
    await db.flush()

    r = await client.post(
        f"/api/v1/tickets/{ticket['id']}/status",
        json={"status": "RESOLVED"},
        headers=headers,
    )
    sla = r.json()["sla"]
    assert sla["resolution_breached"] is True
    assert sla["resolution_time_seconds"] is not None