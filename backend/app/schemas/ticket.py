"""Ticket request/response schemas."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import (
    TicketEventType,
    TicketPriority,
    TicketSource,
    TicketStatus,
    UserRole,
)


# ---------- nested summaries ----------


class TicketCustomerSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: EmailStr
    full_name: str


class TicketUserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: EmailStr
    full_name: str
    role: UserRole


class TicketTeamSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str


class TicketCategorySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str


class TicketSLAResponse(BaseModel):
    policy_id: UUID | None
    policy_name: str | None
    first_response_due_at: datetime | None
    first_response_at: datetime | None
    resolution_due_at: datetime | None
    resolved_at: datetime | None
    first_response_breached: bool
    resolution_breached: bool
    sla_breached: bool
    first_response_time_seconds: int | None
    resolution_time_seconds: int | None


# ---------- ticket responses ----------


class TicketResponse(BaseModel):
    id: UUID
    organization_id: UUID
    title: str
    description: str
    status: TicketStatus
    priority: TicketPriority
    source: TicketSource
    customer: TicketCustomerSummary
    assigned_agent: TicketUserSummary | None
    team: TicketTeamSummary | None
    category: TicketCategorySummary | None
    sla: TicketSLAResponse | None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None
    closed_at: datetime | None


class TicketListResponse(BaseModel):
    items: list[TicketResponse]
    total: int
    page: int
    page_size: int
    pages: int


# ---------- requests ----------


class TicketCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str = Field(min_length=1)
    customer_id: UUID
    category_id: UUID | None = None
    team_id: UUID | None = None
    assigned_agent_id: UUID | None = None
    priority: TicketPriority = TicketPriority.MEDIUM
    source: TicketSource = TicketSource.WEB


class TicketUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = Field(default=None, min_length=1)
    category_id: UUID | None = None


class TicketAssignRequest(BaseModel):
    assigned_agent_id: UUID | None = None
    team_id: UUID | None = None
    note: str | None = Field(default=None, max_length=1000)


class TicketStatusChangeRequest(BaseModel):
    status: TicketStatus
    note: str | None = Field(default=None, max_length=1000)


class TicketPriorityChangeRequest(BaseModel):
    priority: TicketPriority
    note: str | None = Field(default=None, max_length=1000)


class TicketCommentCreateRequest(BaseModel):
    body: str = Field(min_length=1, max_length=50_000)
    is_internal: bool = False


class TicketCommentResponse(BaseModel):
    id: UUID
    organization_id: UUID
    ticket_id: UUID
    author: TicketUserSummary | None
    body: str
    is_internal: bool
    created_at: datetime
    updated_at: datetime


class TicketCommentListResponse(BaseModel):
    items: list[TicketCommentResponse]
    total: int


class TicketEventResponse(BaseModel):
    id: UUID
    organization_id: UUID
    ticket_id: UUID
    actor: TicketUserSummary | None
    event_type: TicketEventType
    from_value: str | None
    to_value: str | None
    note: str | None
    details: dict[str, Any] | None
    created_at: datetime


class TicketEventListResponse(BaseModel):
    items: list[TicketEventResponse]
    total: int


# ---------- filter / sort types ----------

SortField = Literal[
    "created_at",
    "updated_at",
    "priority",
    "status",
    "resolved_at",
    "title",
]
SortOrder = Literal["asc", "desc"]

class TicketAttachmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    ticket_id: UUID
    comment_id: UUID | None
    uploaded_by_user_id: UUID | None
    file_name: str
    content_type: str
    size_bytes: int
    created_at: datetime