"""Ticket domain: SLA fields on tickets + ticket_events table.

Revision ID: 0003_ticket_domain
Revises: 0002_auth
Create Date: 2026-09-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_ticket_domain"
down_revision: str | None = "0002_auth"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


EVENT_TYPES = (
    "TICKET_CREATED",
    "TICKET_UPDATED",
    "TICKET_ASSIGNED",
    "TICKET_REASSIGNED",
    "STATUS_CHANGED",
    "PRIORITY_CHANGED",
    "COMMENT_ADDED",
    "TICKET_RESOLVED",
    "TICKET_REOPENED",
    "TICKET_CLOSED",
    "SLA_POLICY_APPLIED",
    "SLA_BREACHED",
)


def upgrade() -> None:
    bind = op.get_bind()
    postgresql.ENUM(*EVENT_TYPES, name="ticket_event_type").create(bind, checkfirst=True)
    event_type = postgresql.ENUM(name="ticket_event_type", create_type=False)

    op.add_column(
        "tickets",
        sa.Column(
            "sla_policy_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("slas.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "tickets",
        sa.Column("first_response_due_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "tickets",
        sa.Column("resolution_due_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "tickets",
        sa.Column("first_response_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "tickets",
        sa.Column(
            "sla_breached",
            sa.Boolean,
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.create_index(
        "ix_tickets_org_sla_breached",
        "tickets",
        ["organization_id", "sla_breached"],
    )

    op.create_table(
        "ticket_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "ticket_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tickets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "actor_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("event_type", event_type, nullable=False),
        sa.Column("from_value", sa.String(100), nullable=True),
        sa.Column("to_value", sa.String(100), nullable=True),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("details", postgresql.JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_ticket_events_ticket_created",
        "ticket_events",
        ["ticket_id", "created_at"],
    )
    op.create_index(
        "ix_ticket_events_organization_id", "ticket_events", ["organization_id"]
    )
    op.create_index(
        "ix_ticket_events_org_type",
        "ticket_events",
        ["organization_id", "event_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_ticket_events_org_type", table_name="ticket_events")
    op.drop_index("ix_ticket_events_organization_id", table_name="ticket_events")
    op.drop_index("ix_ticket_events_ticket_created", table_name="ticket_events")
    op.drop_table("ticket_events")

    op.drop_index("ix_tickets_org_sla_breached", table_name="tickets")
    op.drop_column("tickets", "sla_breached")
    op.drop_column("tickets", "first_response_at")
    op.drop_column("tickets", "resolution_due_at")
    op.drop_column("tickets", "first_response_due_at")
    op.drop_column("tickets", "sla_policy_id")

    op.execute("DROP TYPE IF EXISTS ticket_event_type")