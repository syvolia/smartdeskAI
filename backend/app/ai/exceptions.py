"""AI-specific exception types."""

from app.core.exceptions import AppError


class AIUnavailableError(AppError):
    status_code = 503
    code = "ai_unavailable"
    message = "The AI service is temporarily unavailable."


class AITimeoutError(AppError):
    status_code = 504
    code = "ai_timeout"
    message = "The AI service timed out."


class AIInvalidResponseError(AppError):
    status_code = 502
    code = "ai_invalid_response"
    message = "The AI service returned an invalid response."