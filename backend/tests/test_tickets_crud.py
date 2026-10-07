"""Ticket CRUD tests."""

import pytest
from httpx import AsyncClient

from app.models import UserRole
from tests.helpers import authed_customer, authed_user, create_ticket

pytestmark = pytest.mark.asyncio


async def test_create_ticket_as_agent(
    client: AsyncClient, make_org, make_user, make_customer
) -> None:
    org, _, headers = await authed_user(make_org, make_user, UserRole.AGENT)
    customer = await make_customer(org=org)

    body = await create_ticket(client, headers, customer_id=customer.id)
    assert body["status"] == "OPEN"
    assert body["priority"] == "MEDIUM"
    assert body["customer"]["id"] == str(customer.id)
    assert body["organization_id"] == str(org.id)


async def test_create_ticket_applies_sla(
    client: AsyncClient, db, make_org, make_user, make_customer
) -> None:
    from app.models import SLA, TicketPriority

    org, _, headers = await authed_user(make_org, make_user, UserRole.ADMIN)
    await db.flush()
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
    customer = await make_customer(org=org)

    body = await create_ticket(client, headers, customer_id=customer.id)
    assert body["sla"]["policy_name"] == "Standard"
    assert body["sla"]["first_response_due_at"] is not None
    assert body["sla"]["resolution_due_at"] is not None


async def test_create_ticket_customer_locked_to_self(
    client: AsyncClient, make_org, make_user, make_customer
) -> None:
    org, _, me_customer, headers = await authed_customer(
        make_org, make_user, make_customer
    )
    other_customer = await make_customer(org=org)

    r = await client.post(
        "/api/v1/tickets",
        json={
            "title": "x",
            "description": "y",
            "customer_id": str(other_customer.id),
        },
        headers=headers,
    )
    assert r.status_code == 403


async def test_create_ticket_customer_ok(
    client: AsyncClient, make_org, make_user, make_customer
) -> None:
    _, _, customer, headers = await authed_customer(
        make_org, make_user, make_customer
    )
    body = await create_ticket(client, headers, customer_id=customer.id)
    assert body["customer"]["id"] == str(customer.id)


async def test_create_ticket_unknown_customer_404(
    client: AsyncClient, make_org, make_user
) -> None:
    import uuid as _uuid

    _, _, headers = await authed_user(make_org, make_user, UserRole.AGENT)
    r = await client.post(
        "/api/v1/tickets",
        json={
            "title": "x",
            "description": "y",
            "customer_id": str(_uuid.uuid4()),
        },
        headers=headers,
    )
    assert r.status_code == 404


async def test_get_ticket(
    client: AsyncClient, make_org, make_user, make_customer
) -> None:
    org, _, headers = await authed_user(make_org, make_user, UserRole.AGENT)
    customer = await make_customer(org=org)
    created = await create_ticket(client, headers, customer_id=customer.id)

    r = await client.get(f"/api/v1/tickets/{created['id']}", headers=headers)
    assert r.status_code == 200
    assert r.json()["id"] == created["id"]


async def test_get_ticket_404_for_unknown(
    client: AsyncClient, make_org, make_user
) -> None:
    import uuid as _uuid

    _, _, headers = await authed_user(make_org, make_user, UserRole.AGENT)
    r = await client.get(f"/api/v1/tickets/{_uuid.uuid4()}", headers=headers)
    assert r.status_code == 404


async def test_update_ticket(
    client: AsyncClient, make_org, make_user, make_customer
) -> None:
    org, _, headers = await authed_user(make_org, make_user, UserRole.AGENT)
    customer = await make_customer(org=org)
    ticket = await create_ticket(client, headers, customer_id=customer.id)

    r = await client.patch(
        f"/api/v1/tickets/{ticket['id']}",
        json={"title": "New title"},
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["title"] == "New title"


async def test_delete_ticket_requires_admin(
    client: AsyncClient, make_org, make_user, make_customer
) -> None:
    org, _, headers = await authed_user(make_org, make_user, UserRole.AGENT)
    customer = await make_customer(org=org)
    ticket = await create_ticket(client, headers, customer_id=customer.id)

    r = await client.delete(f"/api/v1/tickets/{ticket['id']}", headers=headers)
    assert r.status_code == 403


async def test_delete_ticket_as_admin(
    client: AsyncClient, make_org, make_user, make_customer
) -> None:
    org, _, headers = await authed_user(make_org, make_user, UserRole.ADMIN)
    customer = await make_customer(org=org)
    ticket = await create_ticket(client, headers, customer_id=customer.id)

    r = await client.delete(f"/api/v1/tickets/{ticket['id']}", headers=headers)
    assert r.status_code == 204

    r2 = await client.get(f"/api/v1/tickets/{ticket['id']}", headers=headers)
    assert r2.status_code == 404