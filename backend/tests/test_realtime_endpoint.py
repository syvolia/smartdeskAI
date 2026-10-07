"""End-to-end WebSocket endpoint tests."""

import uuid

import pytest
from starlette.testclient import TestClient

from app.core.security import create_access_token, hash_password
from app.main import app as fastapi_app
from app.models import Organization, User, UserRole

pytestmark = pytest.mark.asyncio


@pytest.fixture
def sync_client(engine):
    # TestClient runs a sync ASGI loop; we point it at the same app.
    # The DB override is done per-test to share the async session.
    return TestClient(fastapi_app)


async def test_ws_rejects_missing_token(sync_client: TestClient) -> None:
    with pytest.raises(Exception):
        # Starlette raises WebSocketDisconnect when the server closes
        # before/at accept.
        with sync_client.websocket_connect("/api/v1/ws") as ws:
            ws.receive_json()


async def test_ws_rejects_invalid_token(sync_client: TestClient) -> None:
    with pytest.raises(Exception):
        with sync_client.websocket_connect("/api/v1/ws?token=not-a-jwt") as ws:
            ws.receive_json()


async def test_ws_accepts_valid_token_and_sends_hello(
    db, make_org, make_user, sync_client: TestClient
) -> None:
    org = await make_org(slug="ws-test")
    user, _ = await make_user(org=org, role=UserRole.AGENT)
    await db.commit()

    token, _ = create_access_token(user.id)
    with sync_client.websocket_connect(f"/api/v1/ws?token={token}") as ws:
        hello = ws.receive_json()
        assert hello["kind"] == "hello"
        assert hello["role"] == "AGENT"


async def test_ws_ping_pong(
    db, make_org, make_user, sync_client: TestClient
) -> None:
    org = await make_org(slug="ws-ping")
    user, _ = await make_user(org=org, role=UserRole.AGENT)
    await db.commit()
    token, _ = create_access_token(user.id)

    with sync_client.websocket_connect(f"/api/v1/ws?token={token}") as ws:
        ws.receive_json()  # hello
        ws.send_json({"kind": "ping"})
        pong = ws.receive_json()
        assert pong["kind"] == "pong"