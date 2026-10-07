"""Knowledge base categories and articles."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ArticleStatus

if TYPE_CHECKING:
    from app.models.knowledge_chunk import KnowledgeChunk
    from app.models.user import User


class KnowledgeBaseCategory(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "knowledge_base_categories"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "name", name="uq_kb_categories_org_name"
        ),
        Index("ix_kb_categories_organization_id", "organization_id"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    articles: Mapped[list["KnowledgeBaseArticle"]] = relationship(
        back_populates="category",
    )

    def __repr__(self) -> str:
        return f"<KnowledgeBaseCategory id={self.id} name={self.name!r}>"


class KnowledgeBaseArticle(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "knowledge_base_articles"
    __table_args__ = (
        UniqueConstraint("organization_id", "slug", name="uq_kb_articles_org_slug"),
        Index("ix_kb_articles_organization_id", "organization_id"),
        Index("ix_kb_articles_org_status", "organization_id", "status"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_base_categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    author_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ArticleStatus] = mapped_column(
        SAEnum(
            ArticleStatus,
            name="article_status",
            values_callable=lambda x: [e.value for e in x],
            native_enum=True,
            validate_strings=True,
        ),
        nullable=False,
        default=ArticleStatus.DRAFT,
        server_default=ArticleStatus.DRAFT.value,
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Hash of the last indexed content (title + body). Used to skip
    # re-embedding when nothing has changed.
    indexed_content_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )

    category: Mapped["KnowledgeBaseCategory | None"] = relationship(
        back_populates="articles"
    )
    author: Mapped["User | None"] = relationship()
    chunks: Mapped[list["KnowledgeChunk"]] = relationship(
        back_populates="article",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="KnowledgeChunk.chunk_index",
    )