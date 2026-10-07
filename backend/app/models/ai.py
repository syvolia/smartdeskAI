"""AI job and suggestion models.

AIJob captures the metadata of a single LLM call for auditing and cost
tracking. AISuggestion captures the structured output, its confidence,
and its acceptance lifecycle so analytics can compute acceptance rates
and resolution contribution later.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import (
    AIJobStatus,
    AIOperation,
    AISuggestionKind,
    AISuggestionStatus,
)


def _enum(cls, name: str) -> SAEnum:
    return SAEnum(
        cls,
        name=name,
        values_callable=lambda x: [e.value for e in x],
        native_enum=True,
        validate_strings=True,
    )


class AIJob(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "ai_jobs"
    __table_args__ = (
        Index("ix_ai_jobs_org_created", "organization_id", "created_at"),
        Index("ix_ai_jobs_ticket_created", "ticket_id", "created_at"),
        Index("ix_ai_jobs_operation", "organization_id", "operation"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    ticket_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tickets.id", ondelete="SET NULL"),
        nullable=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    operation: Mapped[AIOperation] = mapped_column(
        _enum(AIOperation, "ai_operation"), nullable=False
    )
    status: Mapped[AIJobStatus] = mapped_column(
        _enum(AIJobStatus, "ai_job_status"), nullable=False
    )

    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    suggestions: Mapped[list["AISuggestion"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class AISuggestion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "ai_suggestions"
    __table_args__ = (
        Index("ix_ai_suggestions_org_ticket", "organization_id", "ticket_id"),
        Index(
            "ix_ai_suggestions_org_kind_status",
            "organization_id",
            "kind",
            "status",
        ),
        Index("ix_ai_suggestions_created", "organization_id", "created_at"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_jobs.id", ondelete="SET NULL"),
        nullable=True,
    )

    kind: Mapped[AISuggestionKind] = mapped_column(
        _enum(AISuggestionKind, "ai_suggestion_kind"), nullable=False
    )
    status: Mapped[AISuggestionStatus] = mapped_column(
        _enum(AISuggestionStatus, "ai_suggestion_status"),
        nullable=False,
        default=AISuggestionStatus.PENDING,
    )

    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    model: Mapped[str] = mapped_column(String(100), nullable=False)

    accepted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rejected_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    rejected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    job: Mapped["AIJob | None"] = relationship(back_populates="suggestions")