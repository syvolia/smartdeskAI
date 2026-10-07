"""Add TICKET_REASSIGNED and TICKET_REOPENED to notification_type.

Revision ID: 0006_notif_types
Revises: 0005_rag
Create Date: 2026-09-23
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0006_notif_types"
down_revision: str | None = "0005_rag"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE notification_type ADD VALUE IF NOT EXISTS 'TICKET_REASSIGNED'"
    )
    op.execute(
        "ALTER TYPE notification_type ADD VALUE IF NOT EXISTS 'TICKET_REOPENED'"
    )


def downgrade() -> None:
    # Postgres can't drop enum values; this is a no-op.
    pass