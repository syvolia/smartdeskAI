"""AI suggestion request/response schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import (
    AISuggestionKind,
    AISuggestionStatus,
)


class AISuggestionResponse(BaseModel):
    id: UUID
    organization_id: UUID
    ticket_id: UUID
    kind: AISuggestionKind
    status: AISuggestionStatus
    payload: dict[str, Any]
    confidence: float | None
    model: str
    created_at: datetime
    updated_at: datetime
    accepted_at: datetime | None
    rejected_at: datetime | None
    rejection_reason: str | None


class AISuggestionListResponse(BaseModel):
    items: list[AISuggestionResponse]
    total: int


class AIRejectRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class AIAcceptResponse(BaseModel):
    suggestion: AISuggestionResponse