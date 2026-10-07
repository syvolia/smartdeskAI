"""Role guards used by every admin endpoint.

These are the *only* trustworthy authorization checks. Client-side route
guards are cosmetic; if a non-admin somehow hits these routes, the guards
reject the request with 403.
"""

from fastapi import Depends

from app.api.dependencies.auth import get_current_user
from app.core.exceptions import ForbiddenError
from app.models import User, UserRole


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.ADMIN:
        raise ForbiddenError("Administrator access required.")
    return user


def require_staff(user: User = Depends(get_current_user)) -> User:
    """ADMIN or AGENT. Used for read-only endpoints that agents need."""
    if user.role not in (UserRole.ADMIN, UserRole.AGENT):
        raise ForbiddenError("Staff access required.")
    return user