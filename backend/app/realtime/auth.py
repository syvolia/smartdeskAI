"""WebSocket authentication.

The client passes the access token as a query parameter on the WS URL:

    ws://host/api/v1/ws?token=<jwt>

Query strings can appear in server logs. For higher-assurance setups,
switch to a first-message auth handshake. Both schemes work with this
module; only the endpoint changes.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UnauthorizedError
from app.core.security import TokenDecodeError, TokenExpiredError, decode_access_token
from app.models import User


async def authenticate_ws_token(
    token: str, db: AsyncSession
) -> User:
    """Resolve a User from a bearer token. Raises UnauthorizedError on failure."""
    if not token:
        raise UnauthorizedError("Missing token.")

    try:
        payload = decode_access_token(token)
    except TokenExpiredError as exc:
        raise UnauthorizedError("Token has expired.") from exc
    except TokenDecodeError as exc:
        raise UnauthorizedError("Invalid token.") from exc

    subject = payload.get("sub")
    if not subject:
        raise UnauthorizedError("Invalid token payload.")

    try:
        user_id = uuid.UUID(str(subject))
    except ValueError as exc:
        raise UnauthorizedError("Invalid token subject.") from exc

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("User not found or inactive.")

    return user