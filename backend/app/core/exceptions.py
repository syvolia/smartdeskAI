"""Application-level exception hierarchy.

Routers and services raise these; a single global handler converts them into
consistent JSON error responses shaped as `{"error": {...}}`.
"""

from typing import Any


class AppError(Exception):
    """Base class for all expected application errors."""

    status_code: int = 500
    code: str = "internal_error"
    message: str = "An unexpected error occurred."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        details: Any = None,
    ) -> None:
        self.message = message or self.message
        self.code = code or self.code
        self.details = details
        super().__init__(self.message)


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"
    message = "Resource not found."


class ValidationError(AppError):
    status_code = 422
    code = "validation_error"
    message = "Validation failed."


class UnauthorizedError(AppError):
    status_code = 401
    code = "unauthorized"
    message = "Authentication required."


class ForbiddenError(AppError):
    status_code = 403
    code = "forbidden"
    message = "You do not have permission to perform this action."


class ConflictError(AppError):
    status_code = 409
    code = "conflict"
    message = "Resource conflict."


class RateLimitedError(AppError):
    status_code = 429
    code = "rate_limited"
    message = "Too many requests."