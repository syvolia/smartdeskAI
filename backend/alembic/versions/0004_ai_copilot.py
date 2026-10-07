"""AI copilot: ai_jobs and ai_suggestions.

Revision ID: 0004_ai_copilot
Revises: 0003_ticket_domain
Create Date: 2026-09-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_ai_copilot"
down_revision: str | None = "0003_ticket_domain"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


AI_OPERATION_VALUES = (
    "CLASSIFY",
    "SUGGEST_PRIORITY",
    "SUMMARIZE",
    "SUGGEST_RESPONSE",
    "SUGGEST_NEXT_ACTION",
)
AI_JOB_STATUS_VALUES = ("SUCCESS", "FAILED", "TIMEOUT")
AI_SUGGESTION_KIND_VALUES = (
    "CLASSIFICATION",
    "PRIORITY",
    "SUMMARY",
    "SUGGESTED_RESPONSE",
    "NEXT_ACTION",
)
AI_SUGGESTION_STATUS_VALUES = ("PENDING", "ACCEPTED", "REJECTED", "SUPERSEDED")


def upgrade() -> None:
    bind = op.get_bind()
    postgresql.ENUM(*AI_OPERATION_VALUES, name="ai_operation").create(bind, checkfirst=True)
    postgresql.ENUM(*AI_JOB_STATUS_VALUES, name="ai_job_status").create(bind, checkfirst=True)
    postgresql.ENUM(*AI_SUGGESTION_KIND_VALUES, name="ai_suggestion_kind").create(bind, checkfirst=True)
    postgresql.ENUM(*AI_SUGGESTION_STATUS_VALUES, name="ai_suggestion_status").create(bind, checkfirst=True)

    ai_operation = postgresql.ENUM(name="ai_operation", create_type=False)
    ai_job_status = postgresql.ENUM(name="ai_job_status", create_type=False)
    ai_suggestion_kind = postgresql.ENUM(name="ai_suggestion_kind", create_type=False)
    ai_suggestion_status = postgresql.ENUM(name="ai_suggestion_status", create_type=False)

    op.create_table(
        "ai_jobs",
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
            sa.ForeignKey("tickets.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("operation", ai_operation, nullable=False),
        sa.Column("status", ai_job_status, nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("prompt_hash", sa.String(64), nullable=True),
        sa.Column("input_tokens", sa.Integer, nullable=True),
        sa.Column("output_tokens", sa.Integer, nullable=True),
        sa.Column("latency_ms", sa.Integer, nullable=True),
        sa.Column("error_code", sa.String(50), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_ai_jobs_org_created", "ai_jobs", ["organization_id", "created_at"])
    op.create_index("ix_ai_jobs_ticket_created", "ai_jobs", ["ticket_id", "created_at"])
    op.create_index("ix_ai_jobs_operation", "ai_jobs", ["organization_id", "operation"])

    op.create_table(
        "ai_suggestions",
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
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ai_jobs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("kind", ai_suggestion_kind, nullable=False),
        sa.Column("status", ai_suggestion_status, nullable=False, server_default="PENDING"),
        sa.Column("payload", postgresql.JSONB, nullable=False),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column(
            "accepted_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "rejected_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_ai_suggestions_org_ticket",
        "ai_suggestions",
        ["organization_id", "ticket_id"],
    )
    op.create_index(
        "ix_ai_suggestions_org_kind_status",
        "ai_suggestions",
        ["organization_id", "kind", "status"],
    )
    op.create_index(
        "ix_ai_suggestions_created",
        "ai_suggestions",
        ["organization_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_ai_suggestions_created", table_name="ai_suggestions")
    op.drop_index("ix_ai_suggestions_org_kind_status", table_name="ai_suggestions")
    op.drop_index("ix_ai_suggestions_org_ticket", table_name="ai_suggestions")
    op.drop_table("ai_suggestions")

    op.drop_index("ix_ai_jobs_operation", table_name="ai_jobs")
    op.drop_index("ix_ai_jobs_ticket_created", table_name="ai_jobs")
    op.drop_index("ix_ai_jobs_org_created", table_name="ai_jobs")
    op.drop_table("ai_jobs")

    for name in (
        "ai_suggestion_status",
        "ai_suggestion_kind",
        "ai_job_status",
        "ai_operation",
    ):
        op.execute(f"DROP TYPE IF EXISTS {name}")