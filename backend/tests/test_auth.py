"""End-to-end tests for the /auth endpoints."""

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import RefreshToken, User, UserRole

pytestmark = pytest.mark.asyncio


REGISTER_PAYLOAD = {
    "organization_name": "Test Org",
    "organization_slug": "test-org",
    "email": "admin@test-org.test",
    "full_name": "Admin User",
    "password": "Passw0rd!",
}


async def _register(client: AsyncClient, **overrides) -> dict:
    payload = {**REGISTER_PAYLOAD, **overrides}
    r = await client.post("/api/v1/auth/register", json=payload)
    assert r.status_code == 201, r.text
    return r.json()


# ---------------- Register ----------------------------------------------------


async def test_register_creates_org_and_admin(client: AsyncClient, db: AsyncSession) -> None:
    body = await _register(client)

    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["expires_in"] > 0
    assert body["user"]["role"] == UserRole.ADMIN.value
    assert body["user"]["email"] == REGISTER_PAYLOAD["email"]

    # Org and user persisted.
    user = await db.scalar(select(User).where(User.email == REGISTER_PAYLOAD["email"]))
    assert user is not None
    assert user.role == UserRole.ADMIN
    assert user.organization_id == body["user"]["organization_id"]


async def test_register_rejects_duplicate_email(client: AsyncClient) -> None:
    await _register(client)

    r = await client.post(
        "/api/v1/auth/register",
        json={**REGISTER_PAYLOAD, "organization_slug": "other-slug"},
    )
    assert r.status_code == 409


async def test_register_rejects_duplicate_org_slug(client: AsyncClient) -> None:
    await _register(client)

    r = await client.post(
        "/api/v1/auth/register",
        json={**REGISTER_PAYLOAD, "email": "someone-else@test-org.test"},
    )
    assert r.status_code == 409


async def test_register_rejects_short_password(client: AsyncClient) -> None:
    r = await client.post(
        "/api/v1/auth/register",
        json={**REGISTER_PAYLOAD, "password": "short"},
    )
    assert r.status_code == 422


# ---------------- Login -------------------------------------------------------


async def test_login_returns_tokens(client: AsyncClient) -> None:
    await _register(client)

    r = await client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": REGISTER_PAYLOAD["password"]},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["access_token"]
    assert body["refresh_token"]


async def test_login_with_wrong_password_returns_401(client: AsyncClient) -> None:
    await _register(client)

    r = await client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": "wrong-password"},
    )
    assert r.status_code == 401


async def test_login_with_unknown_email_returns_401(client: AsyncClient) -> None:
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@nowhere.test", "password": "whatever123"},
    )
    assert r.status_code == 401


async def test_login_disabled_user_returns_403(
    client: AsyncClient, db: AsyncSession
) -> None:
    await _register(client)
    user = await db.scalar(select(User).where(User.email == REGISTER_PAYLOAD["email"]))
    user.is_active = False
    await db.flush()

    r = await client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": REGISTER_PAYLOAD["password"]},
    )
    assert r.status_code == 403


# ---------------- /me ---------------------------------------------------------


async def test_me_with_valid_token(client: AsyncClient) -> None:
    body = await _register(client)
    token = body["access_token"]

    r = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200
    assert r.json()["email"] == REGISTER_PAYLOAD["email"]


async def test_me_without_token_returns_401(client: AsyncClient) -> None:
    r = await client.get("/api/v1/auth/me")
    assert r.status_code == 401


async def test_me_with_invalid_token_returns_401(client: AsyncClient) -> None:
    r = await client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert r.status_code == 401


async def test_me_with_expired_token_returns_401(
    client: AsyncClient,
    make_expired_access_token,
) -> None:
    body = await _register(client)
    user_id = body["user"]["id"]

    expired = make_expired_access_token(user_id)
    r = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {expired}"}
    )
    assert r.status_code == 401


async def test_me_with_refresh_token_as_access_returns_401(client: AsyncClient) -> None:
    body = await _register(client)

    r = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {body['refresh_token']}"},
    )
    assert r.status_code == 401


async def test_me_with_token_for_deleted_user_returns_401(
    client: AsyncClient, db: AsyncSession, make_valid_access_token
) -> None:
    body = await _register(client)
    user = await db.scalar(select(User).where(User.email == REGISTER_PAYLOAD["email"]))
    user_id = user.id

    await db.delete(user)
    await db.flush()

    token = make_valid_access_token(user_id)
    r = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 401


# ---------------- Refresh -----------------------------------------------------


async def test_refresh_rotates_tokens(client: AsyncClient, db: AsyncSession) -> None:
    body = await _register(client)
    old_refresh = body["refresh_token"]

    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert r.status_code == 200, r.text
    new = r.json()
    assert new["access_token"] != body["access_token"]
    assert new["refresh_token"] != old_refresh

    # Old refresh token should now be marked revoked.
    from app.core.security import hash_token

    stored = await db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_token(old_refresh))
    )
    assert stored is not None
    assert stored.revoked_at is not None

    # Replaying the old refresh token must fail.
    r2 = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": old_refresh}
    )
    assert r2.status_code == 401


async def test_refresh_with_garbage_returns_401(client: AsyncClient) -> None:
    r = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": "x" * 64}
    )
    assert r.status_code == 401


async def test_refresh_with_expired_token_returns_401(
    client: AsyncClient, db: AsyncSession
) -> None:
    body = await _register(client)

    from app.core.security import hash_token

    stored = await db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_token(body["refresh_token"])
        )
    )
    stored.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    await db.flush()

    r = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": body["refresh_token"]}
    )
    assert r.status_code == 401


async def test_refresh_with_access_token_returns_401(client: AsyncClient) -> None:
    body = await _register(client)
    # An access token is a JWT, not an opaque refresh token, so it will
    # not be found by hash lookup.
    r = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": body["access_token"]}
    )
    assert r.status_code == 401


# ---------------- Logout ------------------------------------------------------


async def test_logout_revokes_refresh_token(
    client: AsyncClient, db: AsyncSession
) -> None:
    body = await _register(client)

    r = await client.post(
        "/api/v1/auth/logout", json={"refresh_token": body["refresh_token"]}
    )
    assert r.status_code == 204

    # Same refresh token no longer usable.
    r2 = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": body["refresh_token"]}
    )
    assert r2.status_code == 401