"""Authentication and authorization FastAPI dependencies.

These are the *only* trusted sources of identity and organization context.
The client is never allowed to specify its own organization_id.
"""

import uuid
from collections.abc import Callable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import TokenDecodeError, TokenExpiredError, decode_access_token
from app.db.session import get_db
from app.models import User, UserRole

# auto_error=False so we return our own 401 (not FastAPI's default 403).
_bearer = HTTPBearer(auto_error=False, scheme_name="BearerAuth")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Resolve the authenticated user from a Bearer access token."""
    if credentials is None or not credentials.credentials:
        raise UnauthorizedError("Missing bearer token.")

    try:
        payload = decode_access_token(credentials.credentials)
    except TokenExpiredError as exc:
        raise UnauthorizedError("Access token has expired.") from exc
    except TokenDecodeError as exc:
        raise UnauthorizedError("Invalid access token.") from exc

    subject = payload.get("sub")
    if not subject:
        raise UnauthorizedError("Invalid access token payload.")

    try:
        user_id = uuid.UUID(str(subject))
    except ValueError as exc:
        raise UnauthorizedError("Invalid access token subject.") from exc

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("User not found or inactive.")

    return user


def get_current_org_id(user: User = Depends(get_current_user)) -> uuid.UUID:
    """The authenticated user's organization id.

    This is the single source of truth for tenant context. Endpoints must
    never accept organization_id from request bodies, query params, or
    headers as authority.
    """
    return user.organization_id


def require_roles(*allowed: UserRole) -> Callable[..., object]:
    """Build a dependency that requires the current user to have one of
    the given roles."""

    async def _checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise ForbiddenError("You do not have permission to perform this action.")
        return user

    return _checker


# --- Common role gates ---------------------------------------------------------
#
# Admin implies nothing here beyond admin — this is deliberate, since an
# admin is a superset of agent privileges but not of customer privileges.
#
# require_agent grants access to admins too, since admins commonly operate
# as agents.

require_admin = require_roles(UserRole.ADMIN)
require_agent = require_roles(UserRole.ADMIN, UserRole.AGENT)
require_customer = require_roles(UserRole.CUSTOMER)