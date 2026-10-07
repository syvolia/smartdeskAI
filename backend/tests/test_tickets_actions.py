"""Assignment, status, priority, comments."""

import pytest
from httpx import AsyncClient

from app.models import UserRole
from tests.helpers import authed_user, create_ticket

pytestmark = pytest.mark.asyncio


async def test_assign_ticket(
    client: AsyncClient, make_org, make_user, make_customer
) -> None:
    org, _, headers = await authed_user(make_org, make_user, UserRole.ADMIN)
    agent, _ = await make_user(org=org, role=UserRole.AGENT)
    customer = await make_customer(org=org)
    ticket = await create_ticket(client, headers, customer_id=customer.id)

    r = await client.post(
        f"/api/v1/tickets/{ticket['id']}/assign",
        json={"assigned_agent_id": str(agent.id)},
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["assigned_agent"]["id"] == str(agent.id)


async def test_reassign_ticket(
    client: AsyncClient, make_org, make_user, make_customer
) -> None:
    org, _, headers = await authed_user(make_org, make_user, UserRole.ADMIN)
    a1, _ = await make_user(org=org, role=UserRole.AGENT)
    a2, _ = await make_user(org=org, role=UserRole.AGENT)
    customer = await make_customer(org=org)
    ticket = await create_ticket(client, headers, customer_id=customer.id)

    await client.post(
        f"/api/v1/tickets/{ticket['id']}/assign",
        json={"assigned_agent_id": str(a1.id)},
        headers=headers,
    )
    r = await client.post(
        f"/api/v1/tickets/{ticket['id']}/assign",
        json={"assigned_agent_id": str(a2.id)},
        headers=headers,
    )
    assert r.json()["assigned_agent"]["id"] == str(a2.id)

    events = await client.get(
        f"/api/v1/tickets/{ticket['id']}/events", headers=headers
    )
    types = [e["event_type"] for e in events.json()["items"]]
    assert "TICKET_ASSIGNED" in types
    assert "TICKET_REASSIGNED" in types


async def test_assign_unassign(
    client: AsyncClient, make_org, make_user, make_customer
) -> None:
    org, _, headers = await authed_user(make_org, make_user, UserRole.ADMIN)
    agent, _ = await make_user(org=org, role=UserRole.AGENT)
    customer = await make_customer(org=org)
    ticket = await create_ticket(client, headers, customer_id=customer.id)

    await client.post(
        f"/api/v1/tickets/{ticket['id']}/assign",
        json={"assigned_agent_id": str(agent.id)},
        headers=headers,
    )
    r = await client.post(
        f"/api/v1/tickets/{ticket['id']}/assign",
        json={"assigned_agent_id": None},
        headers=headers,
    )
    assert r.json()["assigned_agent"] is None


async def test_status_change_to_resolved_sets_timestamp(
    client: AsyncClient, make_org, make_user, make_customer
) -> None:
    org, _, headers = await authed_user(make_org, make_user, UserRole.AGENT)
    customer = await make_customer(org=org)
    ticket = await create_ticket(client, headers, customer_id=customer.id)

    r = await client.post(
        f"/api/v1/tickets/{ticket['id']}/status",
        json={"status": "RESOLVED"},
        headers=headers,
    )
    assert r.json()["status"] == "RESOLVED"
    assert r.json()["resolved_at"] is not None


async def test_reopen_clears_resolved_at(
    client: AsyncClient, make_org, make_user, make_customer
) -> None:
    org, _, headers = await authed_user(make_org, make_user, UserRole.AGENT)
    customer = await make_customer(org=org)
    ticket = await create_ticket(client, headers, customer_id=customer.id)

    await client.post(
        f"/api/v1/tickets/{ticket['id']}/status",
        json={"status": "RESOLVED"},
        headers=headers,
    )
    r = await client.post(
        f"/api/v1/tickets/{ticket['id']}/status",
        json={"status": "OPEN"},
        headers=headers,
    )
    assert r.json()["resolved_at"] is None


async def test_priority_change_recalculates_sla(
    client: AsyncClient, db, make_org, make_user, make_customer
) -> None:
    from app.models import SLA, TicketPriority

    org, _, headers = await authed_user(make_org, make_user, UserRole.ADMIN)
    db.add_all(
        [
            SLA(
                organization_id=org.id,
                name="Low",
                priority=TicketPriority.LOW,
                first_response_minutes=480,
                resolution_minutes=2880,
            ),
            SLA(
                organization_id=org.id,
                name="Urgent",
                priority=TicketPriority.URGENT,
                first_response_minutes=15,
                resolution_minutes=240,
            ),
        ]
    )
    await db.flush()
    customer = await make_customer(org=org)
    ticket = await create_ticket(
        client, headers, customer_id=customer.id, priority="LOW"
    )

    r = await client.post(
        f"/api/v1/tickets/{ticket['id']}/priority",
        json={"priority": "URGENT"},
        headers=headers,
    )
    body = r.json()
    assert body["priority"] == "URGENT"
    assert body["sla"]["policy_name"] == "Urgent"


async def test_add_public_and_internal_comments(
    client: AsyncClient, make_org, make_user, make_customer
) -> None:
    org, _, headers = await authed_user(make_org, make_user, UserRole.AGENT)
    customer = await make_customer(org=org)
    ticket = await create_ticket(client, headers, customer_id=customer.id)

    r1 = await client.post(
        f"/api/v1/tickets/{ticket['id']}/comments",
        json={"body": "public hello", "is_internal": False},
        headers=headers,
    )
    assert r1.status_code == 201
    r2 = await client.post(
        f"/api/v1/tickets/{ticket['id']}/comments",
        json={"body": "internal note", "is_internal": True},
        headers=headers,
    )
    assert r2.status_code == 201

    r3 = await client.get(
        f"/api/v1/tickets/{ticket['id']}/comments", headers=headers
    )
    assert r3.json()["total"] == 2


async def test_customer_cannot_post_internal_note(
    client: AsyncClient, make_org, make_user, make_customer
) -> None:
    from tests.helpers import authed_customer

    _, _, customer, headers = await authed_customer(make_org, make_user, make_customer)
    ticket = await create_ticket(client, headers, customer_id=customer.id)

    r = await client.post(
        f"/api/v1/tickets/{ticket['id']}/comments",
        json={"body": "internal", "is_internal": True},
        headers=headers,
    )
    assert r.status_code == 403


async def test_customer_only_sees_public_comments(
    client: AsyncClient, make_org, make_user, make_customer
) -> None:
    from tests.helpers import authed_customer

    org, agent, agent_headers = await authed_user(make_org, make_user, UserRole.AGENT)
    email = f"cust-{org.id.hex[:6]}@example.test"
    customer = await make_customer(org=org, email=email)
    cust_user, _ = await make_user(
        org=org, role=UserRole.CUSTOMER, email=email
    )
    from app.core.security import create_access_token

    token, _ = create_access_token(cust_user.id)
    cust_headers = {"Authorization": f"Bearer {token}"}

    ticket = await create_ticket(client, agent_headers, customer_id=customer.id)

    await client.post(
        f"/api/v1/tickets/{ticket['id']}/comments",
        json={"body": "visible", "is_internal": False},
        headers=agent_headers,
    )
    await client.post(
        f"/api/v1/tickets/{ticket['id']}/comments",
        json={"body": "hidden", "is_internal": True},
        headers=agent_headers,
    )

    r = await client.get(
        f"/api/v1/tickets/{ticket['id']}/comments", headers=cust_headers
    )
    bodies = [c["body"] for c in r.json()["items"]]
    assert bodies == ["visible"]