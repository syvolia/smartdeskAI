"""Role-based authorization tests against the dependency layer."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Organization, UserRole
from app.core.security import create_access_token

pytestmark = pytest.mark.asyncio


async def _token_for(user_id) -> str:
    token, _ = create_access_token(user_id)
    return token


async def _setup_user(
    make_org, make_user, role: UserRole
) -> tuple[Organization, str]:
    org = await make_org()
    user, _ = await make_user(org=org, role=role)
    token = await _token_for(user.id)
    return org, token


# ---------------- /test/me ----------------------------------------------------


async def test_me_requires_auth(scope_client: AsyncClient) -> None:
    r = await scope_client.get("/test/me")
    assert r.status_code == 401


async def test_me_returns_identity(scope_client, make_org, make_user) -> None:
    org, token = await _setup_user(make_org, make_user, UserRole.AGENT)
    r = await scope_client.get(
        "/test/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["org_id"] == str(org.id)
    assert body["role"] == "AGENT"


# ---------------- require_admin ----------------------------------------------


async def test_admin_endpoint_allows_admin(scope_client, make_org, make_user) -> None:
    _, token = await _setup_user(make_org, make_user, UserRole.ADMIN)
    r = await scope_client.get(
        "/test/admin", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200


async def test_admin_endpoint_blocks_agent(scope_client, make_org, make_user) -> None:
    _, token = await _setup_user(make_org, make_user, UserRole.AGENT)
    r = await scope_client.get(
        "/test/admin", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 403


async def test_admin_endpoint_blocks_customer(scope_client, make_org, make_user) -> None:
    _, token = await _setup_user(make_org, make_user, UserRole.CUSTOMER)
    r = await scope_client.get(
        "/test/admin", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 403


async def test_admin_endpoint_requires_auth(scope_client) -> None:
    r = await scope_client.get("/test/admin")
    assert r.status_code == 401


# ---------------- require_agent ----------------------------------------------


async def test_agent_endpoint_allows_admin(scope_client, make_org, make_user) -> None:
    _, token = await _setup_user(make_org, make_user, UserRole.ADMIN)
    r = await scope_client.get(
        "/test/agent", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200


async def test_agent_endpoint_allows_agent(scope_client, make_org, make_user) -> None:
    _, token = await _setup_user(make_org, make_user, UserRole.AGENT)
    r = await scope_client.get(
        "/test/agent", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200


async def test_agent_endpoint_blocks_customer(scope_client, make_org, make_user) -> None:
    _, token = await _setup_user(make_org, make_user, UserRole.CUSTOMER)
    r = await scope_client.get(
        "/test/agent", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 403


# ---------------- require_customer -------------------------------------------


async def test_customer_endpoint_allows_customer(
    scope_client, make_org, make_user
) -> None:
    _, token = await _setup_user(make_org, make_user, UserRole.CUSTOMER)
    r = await scope_client.get(
        "/test/customer", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200


async def test_customer_endpoint_blocks_admin(scope_client, make_org, make_user) -> None:
    _, token = await _setup_user(make_org, make_user, UserRole.ADMIN)
    r = await scope_client.get(
        "/test/customer", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 403


async def test_customer_endpoint_blocks_agent(scope_client, make_org, make_user) -> None:
    _, token = await _setup_user(make_org, make_user, UserRole.AGENT)
    r = await scope_client.get(
        "/test/customer", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 403