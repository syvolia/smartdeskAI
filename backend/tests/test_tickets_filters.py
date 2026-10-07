"""List, filter, sort, paginate, search tests."""

import pytest
from httpx import AsyncClient

from app.models import UserRole
from tests.helpers import authed_user, create_ticket

pytestmark = pytest.mark.asyncio


async def _seed(client, headers, org, make_customer, make_team=None):
    """Create a small deterministic set of tickets."""
    c1 = await make_customer(org=org)
    c2 = await make_customer(org=org)

    t1 = await create_ticket(
        client, headers, customer_id=c1.id, priority="LOW", title="Alpha issue"
    )
    t2 = await create_ticket(
        client, headers, customer_id=c1.id, priority="HIGH", title="Beta error"
    )
    t3 = await create_ticket(
        client, headers, customer_id=c2.id, priority="URGENT", title="Gamma"
    )
    return c1, c2, [t1, t2, t3]


async def test_list_all(
    client: AsyncClient, make_org, make_user, make_customer
) -> None:
    org, _, headers = await authed_user(make_org, make_user, UserRole.AGENT)
    await _seed(client, headers, org, make_customer)

    r = await client.get("/api/v1/tickets", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 3
    assert len(body["items"]) == 3


async def test_filter_by_priority(
    client: AsyncClient, make_org, make_user, make_customer
) -> None:
    org, _, headers = await authed_user(make_org, make_user, UserRole.AGENT)
    await _seed(client, headers, org, make_customer)

    r = await client.get("/api/v1/tickets", params={"priority": "HIGH"}, headers=headers)
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["priority"] == "HIGH"


async def test_filter_by_status(
    client: AsyncClient, make_org, make_user, make_customer
) -> None:
    org, _, headers = await authed_user(make_org, make_user, UserRole.AGENT)
    _, _, tickets = await _seed(client, headers, org, make_customer)
    await client.post(
        f"/api/v1/tickets/{tickets[0]['id']}/status",
        json={"status": "IN_PROGRESS"},
        headers=headers,
    )

    r = await client.get(
        "/api/v1/tickets", params={"status": "IN_PROGRESS"}, headers=headers
    )
    body = r.json()
    assert body["total"] == 1


async def test_filter_by_customer(
    client: AsyncClient, make_org, make_user, make_customer
) -> None:
    org, _, headers = await authed_user(make_org, make_user, UserRole.AGENT)
    c1, c2, _ = await _seed(client, headers, org, make_customer)

    r = await client.get(
        "/api/v1/tickets",
        params={"customer_id": str(c1.id)},
        headers=headers,
    )
    assert r.json()["total"] == 2


async def test_search_title_and_description(
    client: AsyncClient, make_org, make_user, make_customer
) -> None:
    org, _, headers = await authed_user(make_org, make_user, UserRole.AGENT)
    await _seed(client, headers, org, make_customer)

    r = await client.get(
        "/api/v1/tickets", params={"search": "Beta"}, headers=headers
    )
    assert r.json()["total"] == 1


async def test_sort_by_priority_asc(
    client: AsyncClient, make_org, make_user, make_customer
) -> None:
    org, _, headers = await authed_user(make_org, make_user, UserRole.AGENT)
    await _seed(client, headers, org, make_customer)

    r = await client.get(
        "/api/v1/tickets",
        params={"sort": "priority", "order": "asc"},
        headers=headers,
    )
    priorities = [t["priority"] for t in r.json()["items"]]
    assert priorities == ["LOW", "MEDIUM", "HIGH", "URGENT"][: len(priorities)] or \
        priorities == sorted(priorities, key=["LOW", "MEDIUM", "HIGH", "URGENT"].index)


async def test_pagination(
    client: AsyncClient, make_org, make_user, make_customer
) -> None:
    org, _, headers = await authed_user(make_org, make_user, UserRole.AGENT)
    await _seed(client, headers, org, make_customer)

    r1 = await client.get(
        "/api/v1/tickets", params={"page": 1, "page_size": 2}, headers=headers
    )
    b1 = r1.json()
    assert b1["page"] == 1
    assert b1["page_size"] == 2
    assert b1["pages"] == 2
    assert len(b1["items"]) == 2

    r2 = await client.get(
        "/api/v1/tickets", params={"page": 2, "page_size": 2}, headers=headers
    )
    assert len(r2.json()["items"]) == 1


async def test_filter_by_created_date_range(
    client: AsyncClient, make_org, make_user, make_customer
) -> None:
    from datetime import datetime, timedelta, timezone

    org, _, headers = await authed_user(make_org, make_user, UserRole.AGENT)
    await _seed(client, headers, org, make_customer)

    future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    r = await client.get(
        "/api/v1/tickets",
        params={"created_from": future},
        headers=headers,
    )
    assert r.json()["total"] == 0