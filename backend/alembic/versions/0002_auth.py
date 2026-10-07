"""Auth: add CUSTOMER role, global-unique email, refresh_tokens table.

Revision ID: 0002_auth
Revises: 0001_initial
Create Date: 2026-09-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_auth"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Add CUSTOMER to user_role enum.
    #    PG12+ allows ADD VALUE inside a transaction as long as the new
    #    value is not used in the same transaction — we don't use it here.
    op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'CUSTOMER'")

    # 2. Replace per-org email uniqueness with global uniqueness.
    op.drop_constraint("uq_users_org_email", "users", type_="unique")
    op.create_unique_constraint("uq_users_email", "users", ["email"])

    # 3. Refresh tokens table.
    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_expires_at", "refresh_tokens", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_refresh_tokens_expires_at", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_user_id", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")

    op.drop_constraint("uq_users_email", "users", type_="unique")
    op.create_unique_constraint(
        "uq_users_org_email", "users", ["organization_id", "email"]
    )

    # Note: removing enum values is not supported by Postgres.
    # Downgrade leaves CUSTOMER in place; acceptable for a portfolio project.