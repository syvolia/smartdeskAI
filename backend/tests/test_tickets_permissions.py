"""Cross-tenant and role-based authorization for tickets."""

import pytest
from httpx import AsyncClient

from app.models import UserRole
from tests.helpers import authed_customer, authed_user, create_ticket

pytestmark = pytest.mark.asyncio


async def test_customer_sees_only_own_tickets(
    client: AsyncClient, make_org, make_user, make_customer
) -> None:
    org, _, cust_user, cust_headers = await authed_customer(
        make_org, make_user, make_customer
    )
    _, _, agent_headers = await authed_user(make_org, make_user, UserRole.AGENT)

    # One ticket for the CUSTOMER user, plus a ticket for another customer.
    own_ticket = await create_ticket(
        client, cust_headers, customer_id=cust_user.id
    )
    other_customer = await make_customer(org=org)
    await create_ticket(client, agent_headers, customer_id=other_customer.id)

    r = await client.get("/api/v1/tickets", headers=cust_headers)
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == own_ticket["id"]


async def test_customer_cannot_get_another_orgs_ticket(
    client: AsyncClient, make_org, make_user, make_customer
) -> None:
    org_a, _, cust_a, headers_a = await authed_customer(
        make_org, make_user, make_customer
    )
    org_b, _, headers_b = await authed_user(make_org, make_user, UserRole.AGENT)

    b_customer = await make_customer(org=org_b)
    b_ticket = await create_ticket(client, headers_b, customer_id=b_customer.id)

    r = await client.get(f"/api/v1/tickets/{b_ticket['id']}", headers=headers_a)
    assert r.status_code == 404


async def test_agent_cannot_get_other_org_ticket(
    client: AsyncClient, make_org, make_user, make_customer
) -> None:
    org_a, _, headers_a = await authed_user(make_org, make_user, UserRole.AGENT)
    org_b, _, headers_b = await authed_user(make_org, make_user, UserRole.AGENT)

    b_customer = await make_customer(org=org_b)
    b_ticket = await create_ticket(client, headers_b, customer_id=b_customer.id)

    r = await client.get(f"/api/v1/tickets/{b_ticket['id']}", headers=headers_a)
    assert r.status_code == 404


async def test_agent_cannot_update_other_org_ticket(
    client: AsyncClient, make_org, make_user, make_customer
) -> None:
    org_a, _, headers_a = await authed_user(make_org, make_user, UserRole.AGENT)
    org_b, _, headers_b = await authed_user(make_org, make_user, UserRole.AGENT)
    b_customer = await make_customer(org=org_b)
    b_ticket = await create_ticket(client, headers_b, customer_id=b_customer.id)

    r = await client.patch(
        f"/api/v1/tickets/{b_ticket['id']}",
        json={"title": "hacked"},
        headers=headers_a,
    )
    assert r.status_code == 404


async def test_agent_cannot_assign_other_org_ticket(
    client: AsyncClient, make_org, make_user, make_customer
) -> None:
    org_a, agent_a, headers_a = await authed_user(
        make_org, make_user, UserRole.AGENT
    )
    org_b, _, headers_b = await authed_user(make_org, make_user, UserRole.AGENT)
    b_customer = await make_customer(org=org_b)
    b_ticket = await create_ticket(client, headers_b, customer_id=b_customer.id)

    r = await client.post(
        f"/api/v1/tickets/{b_ticket['id']}/assign",
        json={"assigned_agent_id": str(agent_a.id)},
        headers=headers_a,
    )
    assert r.status_code == 404


async def test_agent_cannot_assign_from_other_org(
    client: AsyncClient, make_org, make_user, make_customer
) -> None:
    """Attempt to assign an own ticket to an agent in a different org."""
    org_a, _, headers_a = await authed_user(make_org, make_user, UserRole.ADMIN)
    org_b, agent_b, _ = await authed_user(make_org, make_user, UserRole.AGENT)
    a_customer = await make_customer(org=org_a)
    a_ticket = await create_ticket(client, headers_a, customer_id=a_customer.id)

    r = await client.post(
        f"/api/v1/tickets/{a_ticket['id']}/assign",
        json={"assigned_agent_id": str(agent_b.id)},
        headers=headers_a,
    )
    assert r.status_code == 422


async def test_customer_cannot_change_status(
    client: AsyncClient, make_org, make_user, make_customer
) -> None:
    _, _, customer, headers = await authed_customer(make_org, make_user, make_customer)
    ticket = await create_ticket(client, headers, customer_id=customer.id)

    r = await client.post(
        f"/api/v1/tickets/{ticket['id']}/status",
        json={"status": "RESOLVED"},
        headers=headers,
    )
    assert r.status_code == 403


async def test_customer_cannot_delete(
    client: AsyncClient, make_org, make_user, make_customer
) -> None:
    _, _, customer, headers = await authed_customer(make_org, make_user, make_customer)
    ticket = await create_ticket(client, headers, customer_id=customer.id)

    r = await client.delete(f"/api/v1/tickets/{ticket['id']}", headers=headers)
    assert r.status_code == 403


async def test_unauthenticated_request_401(client: AsyncClient) -> None:
    r = await client.get("/api/v1/tickets")
    assert r.status_code == 401

    r = await client.post(
        "/api/v1/tickets",
        json={"title": "x", "description": "y", "customer_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert r.status_code == 401