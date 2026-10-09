"""Admin request/response schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.email import EmailStr

from app.models.enums import (
    ArticleStatus,
    NotificationType,
    TicketPriority,
    UserRole,
)


# ---------- organization ----------


class OrganizationProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    plan: str
    settings: dict[str, Any]
    ai_config: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class OrganizationUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    plan: str | None = Field(default=None, max_length=32)
    settings: dict[str, Any] | None = None


class AIConfigUpdateRequest(BaseModel):
    ai_config: dict[str, Any]


# ---------- users ----------


class AdminUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AdminUserListResponse(BaseModel):
    items: list[AdminUserResponse]
    total: int


class AdminUserCreateRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    role: UserRole = UserRole.AGENT
    password: str = Field(min_length=8, max_length=128)


class AdminUserUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    role: UserRole | None = None
    is_active: bool | None = None


# ---------- teams ----------


class TeamMemberSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    full_name: str
    email: EmailStr
    role: UserRole
    role_in_team: str | None


class TeamResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    description: str | None
    members: list[TeamMemberSummary]
    created_at: datetime
    updated_at: datetime


class TeamListResponse(BaseModel):
    items: list[TeamResponse]
    total: int


class TeamCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)


class TeamUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)


class TeamMemberAddRequest(BaseModel):
    user_id: UUID
    role_in_team: str | None = Field(default=None, max_length=50)


# ---------- ticket categories ----------


class TicketCategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class TicketCategoryListResponse(BaseModel):
    items: list[TicketCategoryResponse]
    total: int


class TicketCategoryCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)


class TicketCategoryUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)


# ---------- SLAs ----------


class SLAResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    name: str
    priority: TicketPriority
    first_response_minutes: int
    resolution_minutes: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class SLAListResponse(BaseModel):
    items: list[SLAResponse]
    total: int


class SLACreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    priority: TicketPriority
    first_response_minutes: int = Field(ge=1, le=60 * 24 * 30)
    resolution_minutes: int = Field(ge=1, le=60 * 24 * 30)
    is_active: bool = True


class SLAUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    priority: TicketPriority | None = None
    first_response_minutes: int | None = Field(
        default=None, ge=1, le=60 * 24 * 30
    )
    resolution_minutes: int | None = Field(
        default=None, ge=1, le=60 * 24 * 30
    )
    is_active: bool | None = None


# ---------- notification preferences ----------


class ChannelPreference(BaseModel):
    email: bool = True
    in_app: bool = True


class NotificationPreferencesResponse(BaseModel):
    user_id: UUID
    organization_id: UUID
    prefs: dict[str, ChannelPreference]


class NotificationPreferencesUpdateRequest(BaseModel):
    prefs: dict[str, ChannelPreference]


# ---------- knowledge base (admin view of articles) ----------


class KBArticleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    category_id: UUID | None
    author_user_id: UUID | None
    title: str
    slug: str
    body: str
    status: ArticleStatus
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime


class KBArticleListResponse(BaseModel):
    items: list[KBArticleResponse]
    total: int


class KBArticleCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    slug: str = Field(min_length=2, max_length=200)
    body: str = Field(min_length=1)
    category_id: UUID | None = None
    status: ArticleStatus = ArticleStatus.DRAFT


class KBArticleUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    body: str | None = Field(default=None, min_length=1)
    category_id: UUID | None = None
    status: ArticleStatus | None = None


class KBCategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class KBCategoryListResponse(BaseModel):
    items: list[KBCategoryResponse]
    total: int


class KBCategoryCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)


class AdminOverviewResponse(BaseModel):
    users: int
    agents: int
    teams: int
    categories: int
    slas: int
    kb_articles: int
    kb_published: int
    plan: str
    ai_enabled: bool


__all__ = [
    "AdminOverviewResponse",
    "AdminUserCreateRequest",
    "AdminUserListResponse",
    "AdminUserResponse",
    "AdminUserUpdateRequest",
    "AIConfigUpdateRequest",
    "ChannelPreference",
    "KBCategoryCreateRequest",
    "KBCategoryListResponse",
    "KBCategoryResponse",
    "KBArticleCreateRequest",
    "KBArticleListResponse",
    "KBArticleResponse",
    "KBArticleUpdateRequest",
    "NotificationPreferencesResponse",
    "NotificationPreferencesUpdateRequest",
    "OrganizationProfileResponse",
    "OrganizationUpdateRequest",
    "SLACreateRequest",
    "SLAListResponse",
    "SLAResponse",
    "SLAUpdateRequest",
    "TeamCreateRequest",
    "TeamListResponse",
    "TeamMemberAddRequest",
    "TeamMemberSummary",
    "TeamResponse",
    "TeamUpdateRequest",
    "TicketCategoryCreateRequest",
    "TicketCategoryListResponse",
    "TicketCategoryResponse",
    "TicketCategoryUpdateRequest",
]