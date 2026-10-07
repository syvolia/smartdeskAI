"""Shared async helpers for API tests."""

from httpx import AsyncClient

from app.core.security import create_access_token
from app.models import Customer, Organization, User, UserRole


async def authed_user(
    make_org,
    make_user,
    role: UserRole = UserRole.AGENT,
    **user_kwargs,
) -> tuple[Organization, User, dict[str, str]]:
    org = await make_org()
    user, _ = await make_user(org=org, role=role, **user_kwargs)
    token, _ = create_access_token(user.id)
    return org, user, {"Authorization": f"Bearer {token}"}


async def authed_customer(
    make_org, make_user, make_customer
) -> tuple[Organization, User, Customer, dict[str, str]]:
    """Create an org + a CUSTOMER user linked to a Customer record by email."""
    org = await make_org()
    email = f"cust-{org.id.hex[:6]}@example.test"
    customer = await make_customer(org=org, email=email)
    user, _ = await make_user(org=org, role=UserRole.CUSTOMER, email=email)
    token, _ = create_access_token(user.id)
    return org, user, customer, {"Authorization": f"Bearer {token}"}


async def create_ticket(
    client: AsyncClient, headers: dict[str, str], *, customer_id, **overrides
):
    payload = {
        "title": "Help needed",
        "description": "Something is broken.",
        "customer_id": str(customer_id),
        "priority": "MEDIUM",
        "source": "WEB",
        **overrides,
    }
    r = await client.post("/api/v1/tickets", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()