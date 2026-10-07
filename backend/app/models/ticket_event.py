"""Append-only audit trail for ticket activity."""

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Enum as SAEnum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin
from app.models.enums import TicketEventType

if TYPE_CHECKING:
    from app.models.ticket import Ticket
    from app.models.user import User


class TicketEvent(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    __tablename__ = "ticket_events"
    __table_args__ = (
        Index("ix_ticket_events_ticket_created", "ticket_id", "created_at"),
        Index("ix_ticket_events_organization_id", "organization_id"),
        Index("ix_ticket_events_org_type", "organization_id", "event_type"),
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
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    event_type: Mapped[TicketEventType] = mapped_column(
        SAEnum(
            TicketEventType,
            name="ticket_event_type",
            values_callable=lambda x: [e.value for e in x],
            native_enum=True,
            validate_strings=True,
        ),
        nullable=False,
    )
    from_value: Mapped[str | None] = mapped_column(String(100), nullable=True)
    to_value: Mapped[str | None] = mapped_column(String(100), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    ticket: Mapped["Ticket"] = relationship(back_populates="events")
    actor: Mapped["User | None"] = relationship()

    def __repr__(self) -> str:
        return f"<TicketEvent id={self.id} type={self.event_type.value}>"