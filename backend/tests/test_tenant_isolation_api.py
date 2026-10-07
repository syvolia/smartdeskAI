"""Cross-tenant access tests.

These prove that a user authenticated into Organization A cannot read,
list, or infer resources belonging to Organization B via the API — even
when the client tries to pass another org's id explicitly.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models import UserRole

pytestmark = pytest.mark.asyncio


async def _make_agent_token(make_org, make_user):
    org = await make_org()
    user, _ = await make_user(org=org, role=UserRole.AGENT)
    token, _ = create_access_token(user.id)
    return org, user, token


# ---------------- /test/me is scoped by token --------------------------------


async def test_me_reflects_token_owner_only(scope_client, make_org, make_user) -> None:
    org_a, _, token_a = await _make_agent_token(make_org, make_user)
    org_b, _, token_b = await _make_agent_token(make_org, make_user)

    ra = await scope_client.get(
        "/test/me", headers={"Authorization": f"Bearer {token_a}"}
    )
    rb = await scope_client.get(
        "/test/me", headers={"Authorization": f"Bearer {token_b}"}
    )

    assert ra.json()["org_id"] == str(org_a.id)
    assert rb.json()["org_id"] == str(org_b.id)
    assert ra.json()["org_id"] != rb.json()["org_id"]


# ---------------- Cross-tenant reads are blocked -----------------------------


async def test_org_customers_returns_only_own_org(
    scope_client, make_org, make_user, make_customer
) -> None:
    org_a, _, token_a = await _make_agent_token(make_org, make_user)
    org_b = await make_org()
    await make_customer(org=org_b)

    # org_a has no customers yet; create one to make the test meaningful.
    a_customer = await make_customer(org=org_a)

    r = await scope_client.get(
        "/test/org-customers", headers={"Authorization": f"Bearer {token_a}"}
    )
    assert r.status_code == 200
    ids = r.json()
    assert str(a_customer.id) in ids
    # Every returned customer must belong to org_a.
    assert len(ids) == 1


async def test_org_tickets_returns_only_own_org(
    scope_client, make_org, make_user, make_customer, make_ticket
) -> None:
    org_a, _, token_a = await _make_agent_token(make_org, make_user)
    org_b = await make_org()

    a_cust = await make_customer(org=org_a)
    b_cust = await make_customer(org=org_b)

    a_ticket = await make_ticket(org=org_a, customer=a_cust, title="A ticket")
    b_ticket = await make_ticket(org=org_b, customer=b_cust, title="B ticket")

    r = await scope_client.get(
        "/test/org-tickets", headers={"Authorization": f"Bearer {token_a}"}
    )
    assert r.status_code == 200
    ids = r.json()
    assert str(a_ticket.id) in ids
    assert str(b_ticket.id) not in ids


# ---------------- Client-supplied org id is ignored --------------------------


async def test_client_supplied_org_id_is_ignored(
    scope_client, make_org, make_user, make_customer
) -> None:
    """Even if the client explicitly passes another org's id as a query
    parameter, the server must use the token-derived org."""
    org_a, _, token_a = await _make_agent_token(make_org, make_user)
    org_b = await make_org()
    b_customer = await make_customer(org=org_b)

    r = await scope_client.get(
        "/test/org-customers",
        params={"organization_id": str(org_b.id), "org_id": str(org_b.id)},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert r.status_code == 200
    ids = r.json()
    # org_b's customer must NOT be visible.
    assert str(b_customer.id) not in ids


async def test_client_supplied_org_id_in_header_is_ignored(
    scope_client, make_org, make_user, make_customer
) -> None:
    org_a, _, token_a = await _make_agent_token(make_org, make_user)
    org_b = await make_org()
    b_customer = await make_customer(org=org_b)

    r = await scope_client.get(
        "/test/org-customers",
        headers={
            "Authorization": f"Bearer {token_a}",
            "X-Organization-Id": str(org_b.id),
        },
    )
    assert r.status_code == 200
    assert str(b_customer.id) not in r.json()


# ---------------- Token swap between orgs ------------------------------------


async def test_token_from_org_a_does_not_grant_org_b_view(
    scope_client, make_org, make_user, make_customer
) -> None:
    org_a, _, token_a = await _make_agent_token(make_org, make_user)
    org_b = await make_org()
    a_customer = await make_customer(org=org_a)
    await make_customer(org=org_b)

    # org_a's token sees only org_a's customer.
    r = await scope_client.get(
        "/test/org-customers", headers={"Authorization": f"Bearer {token_a}"}
    )
    ids = r.json()
    assert ids == [str(a_customer.id)]