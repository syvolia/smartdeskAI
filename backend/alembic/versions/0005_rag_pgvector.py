"""RAG: knowledge_chunks table with pgvector embeddings.

Revision ID: 0005_rag
Revises: 0004_ai_copilot
Create Date: 2026-09-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0005_rag"
down_revision: str | None = "0004_ai_copilot"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EMBEDDING_DIMENSION = 1536


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    op.add_column(
        "knowledge_base_articles",
        sa.Column("indexed_content_hash", sa.String(64), nullable=True),
    )

    op.create_table(
        "knowledge_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "article_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("knowledge_base_articles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("token_count", sa.Integer, nullable=False),
        sa.Column(
            "embedding", Vector(EMBEDDING_DIMENSION), nullable=False
        ),
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
        sa.UniqueConstraint(
            "article_id", "chunk_index", name="uq_knowledge_chunks_article_index"
        ),
    )
    op.create_index(
        "ix_knowledge_chunks_organization_id",
        "knowledge_chunks",
        ["organization_id"],
    )
    op.create_index(
        "ix_knowledge_chunks_org_article",
        "knowledge_chunks",
        ["organization_id", "article_id"],
    )

    # HNSW index for cosine similarity. Requires pgvector 0.5+.
    op.execute(
        "CREATE INDEX ix_knowledge_chunks_embedding_hnsw "
        "ON knowledge_chunks USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_knowledge_chunks_embedding_hnsw")
    op.drop_index(
        "ix_knowledge_chunks_org_article", table_name="knowledge_chunks"
    )
    op.drop_index(
        "ix_knowledge_chunks_organization_id", table_name="knowledge_chunks"
    )
    op.drop_table("knowledge_chunks")
    op.drop_column("knowledge_base_articles", "indexed_content_hash")