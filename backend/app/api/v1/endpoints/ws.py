"""WebSocket endpoint.

Clients connect once per session. The server authenticates the JWT,
registers the connection in the org-scoped manager, and forwards events
until the client disconnects.

The endpoint sends a small `{"kind": "hello", ...}` frame on connect so
clients can confirm the connection is live and up-to-date. Clients can
send `{"kind": "ping"}` for keepalive; the server replies with `pong`.
"""

import uuid

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UnauthorizedError
from app.core.logging import get_logger
from app.db.session import get_db
from app.realtime.auth import authenticate_ws_token
from app.realtime.manager import ConnectionManager, get_connection_manager

router = APIRouter(tags=["realtime"])
logger = get_logger(__name__)


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(default=""),
    manager: ConnectionManager = Depends(get_connection_manager),
) -> None:
    # WebSocket endpoints in FastAPI don't use the HTTP dependency
    # injection pipeline the same way; we open a session manually.
    from app.db.session import SessionLocal

    async with SessionLocal() as db:
        try:
            user = await authenticate_ws_token(token, db)
        except UnauthorizedError as exc:
            # Accept-then-close so the client receives an explicit code.
            await websocket.accept()
            await websocket.close(code=4401, reason=str(exc))
            return

        conn = await manager.connect(
            websocket,
            user_id=user.id,
            user_email=user.email,
            organization_id=user.organization_id,
            role=user.role,
        )

        try:
            await manager.send_to_connection(
                conn,
                {
                    "kind": "hello",
                    "user_id": str(user.id),
                    "org_id": str(user.organization_id),
                    "role": user.role.value,
                },
            )

            while True:
                message = await websocket.receive_json()
                kind = message.get("kind") if isinstance(message, dict) else None
                if kind == "ping":
                    await manager.send_to_connection(
                        conn, {"kind": "pong"}
                    )
                # All other client messages are ignored; the client
                # never mutates state over the socket.
        except WebSocketDisconnect:
            pass
        except Exception:
            logger.exception("ws_connection_error")
        finally:
            await manager.disconnect(conn)