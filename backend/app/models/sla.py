"""SLA policy model."""

import uuid

from sqlalchemy import Boolean, Enum as SAEnum, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import TicketPriority


class SLA(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "slas"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_slas_org_name"),
        Index("ix_slas_organization_id", "organization_id"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    priority: Mapped[TicketPriority] = mapped_column(
        SAEnum(
            TicketPriority,
            name="ticket_priority",
            values_callable=lambda x: [e.value for e in x],
            native_enum=True,
            create_type=False,
        ),
        nullable=False,
    )
    first_response_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    resolution_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:
        return f"<SLA id={self.id} name={self.name!r} priority={self.priority.value}>"