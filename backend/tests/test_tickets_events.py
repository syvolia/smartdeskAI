"""Activity trail tests."""

import pytest
from httpx import AsyncClient

from app.models import UserRole
from tests.helpers import authed_user, create_ticket

pytestmark = pytest.mark.asyncio


async def _event_types(client, headers, ticket_id):
    r = await client.get(f"/api/v1/tickets/{ticket_id}/events", headers=headers)
    return [e["event_type"] for e in r.json()["items"]]


async def test_ticket_created_event(
    client: AsyncClient, make_org, make_user, make_customer
) -> None:
    org, _, headers = await authed_user(make_org, make_user, UserRole.AGENT)
    customer = await make_customer(org=org)
    ticket = await create_ticket(client, headers, customer_id=customer.id)

    types = await _event_types(client, headers, ticket["id"])
    assert "TICKET_CREATED" in types


async def test_assignment_event(
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

    types = await _event_types(client, headers, ticket["id"])
    assert "TICKET_ASSIGNED" in types


async def test_status_event(
    client: AsyncClient, make_org, make_user, make_customer
) -> None:
    org, _, headers = await authed_user(make_org, make_user, UserRole.AGENT)
    customer = await make_customer(org=org)
    ticket = await create_ticket(client, headers, customer_id=customer.id)

    await client.post(
        f"/api/v1/tickets/{ticket['id']}/status",
        json={"status": "IN_PROGRESS"},
        headers=headers,
    )
    types = await _event_types(client, headers, ticket["id"])
    assert "STATUS_CHANGED" in types


async def test_resolved_and_reopened_events(
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
    await client.post(
        f"/api/v1/tickets/{ticket['id']}/status",
        json={"status": "OPEN"},
        headers=headers,
    )

    types = await _event_types(client, headers, ticket["id"])
    assert "TICKET_RESOLVED" in types
    assert "TICKET_REOPENED" in types


async def test_priority_event(
    client: AsyncClient, make_org, make_user, make_customer
) -> None:
    org, _, headers = await authed_user(make_org, make_user, UserRole.AGENT)
    customer = await make_customer(org=org)
    ticket = await create_ticket(client, headers, customer_id=customer.id)

    await client.post(
        f"/api/v1/tickets/{ticket['id']}/priority",
        json={"priority": "URGENT"},
        headers=headers,
    )
    types = await _event_types(client, headers, ticket["id"])
    assert "PRIORITY_CHANGED" in types


async def test_comment_event(
    client: AsyncClient, make_org, make_user, make_customer
) -> None:
    org, _, headers = await authed_user(make_org, make_user, UserRole.AGENT)
    customer = await make_customer(org=org)
    ticket = await create_ticket(client, headers, customer_id=customer.id)

    await client.post(
        f"/api/v1/tickets/{ticket['id']}/comments",
        json={"body": "hi"},
        headers=headers,
    )
    types = await _event_types(client, headers, ticket["id"])
    assert "COMMENT_ADDED" in types


async def test_events_are_tenant_scoped(
    client: AsyncClient, make_org, make_user, make_customer
) -> None:
    org_a, _, headers_a = await authed_user(make_org, make_user, UserRole.AGENT)
    org_b, _, headers_b = await authed_user(make_org, make_user, UserRole.AGENT)
    customer_a = await make_customer(org=org_a)
    ticket_a = await create_ticket(client, headers_a, customer_id=customer_a.id)

    r = await client.get(
        f"/api/v1/tickets/{ticket_a['id']}/events", headers=headers_b
    )
    assert r.status_code == 404