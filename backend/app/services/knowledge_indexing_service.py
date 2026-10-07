"""Embedding pipeline for knowledge-base articles.

Orchestrates: clean → chunk → embed → store → associate with article.
Idempotent: re-running on unchanged content is a no-op thanks to the
`indexed_content_hash` field on the article.

In Phase 10, this can move to a background worker. For now it's called
inline from the article create/update flow.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.chunking import chunk_content, content_hash, estimate_tokens
from app.ai.embeddings.provider import EmbeddingProvider
from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.models import KnowledgeBaseArticle, KnowledgeChunk
from app.repositories.knowledge_chunk_repository import (
    KnowledgeChunkRepository,
)

logger = get_logger(__name__)


class KnowledgeIndexingService:
    def __init__(
        self,
        db: AsyncSession,
        embeddings: EmbeddingProvider,
    ) -> None:
        self.db = db
        self.embeddings = embeddings
        self.chunks = KnowledgeChunkRepository(db)

    async def index_article(
        self,
        article_id: uuid.UUID,
        org_id: uuid.UUID,
        *,
        force: bool = False,
    ) -> int:
        """(Re)index a single article. Returns number of chunks stored.

        If the article's content is unchanged since last indexing and
        `force` is False, this is a no-op.
        """
        article = await self.db.scalar(
            select(KnowledgeBaseArticle).where(
                KnowledgeBaseArticle.id == article_id,
                KnowledgeBaseArticle.organization_id == org_id,
            )
        )
        if article is None:
            raise NotFoundError("Article not found.")

        # Compose the indexed text. Title is included so queries that
        # match the title surface the right article.
        indexed_text = f"{article.title}\n\n{article.body}"
        new_hash = content_hash(indexed_text)

        if not force and article.indexed_content_hash == new_hash:
            logger.info(
                "knowledge_index_skipped",
                article_id=str(article.id),
                org_id=str(org_id),
                reason="content_unchanged",
            )
            return await self.chunks.count_for_article(article.id, org_id)

        chunks_text = chunk_content(
            indexed_text,
            target_tokens=settings.knowledge_chunk_target_tokens,
            overlap_tokens=settings.knowledge_chunk_overlap_tokens,
        )
        if not chunks_text:
            await self.chunks.delete_for_article(article.id, org_id)
            article.indexed_content_hash = new_hash
            await self.db.flush()
            return 0

        vectors, meta = await self.embeddings.embed(
            chunks_text,
            timeout_seconds=settings.openai_timeout_seconds,
        )
        if len(vectors) != len(chunks_text):
            from app.ai.exceptions import AIInvalidResponseError

            raise AIInvalidResponseError(
                "Embedding provider returned the wrong number of vectors."
            )

        # Replace all chunks for this article atomically.
        await self.chunks.delete_for_article(article.id, org_id)

        chunk_models = [
            KnowledgeChunk(
                organization_id=org_id,
                article_id=article.id,
                chunk_index=i,
                content=text,
                content_hash=content_hash(text),
                token_count=estimate_tokens(text),
                embedding=vector,
            )
            for i, (text, vector) in enumerate(zip(chunks_text, vectors, strict=True))
        ]
        await self.chunks.bulk_create(chunk_models)

        article.indexed_content_hash = new_hash
        await self.db.flush()

        logger.info(
            "knowledge_indexed",
            article_id=str(article.id),
            org_id=str(org_id),
            chunks=len(chunk_models),
            provider=meta.provider,
            model=meta.model,
            latency_ms=meta.latency_ms,
        )
        return len(chunk_models)

    async def reindex_organization(
        self, org_id: uuid.UUID
    ) -> dict[str, int]:
        """Force a full reindex for an organization. Admin-only."""
        articles = list(
            (
                await self.db.scalars(
                    select(KnowledgeBaseArticle).where(
                        KnowledgeBaseArticle.organization_id == org_id
                    )
                )
            ).all()
        )
        total_chunks = 0
        for article in articles:
            total_chunks += await self.index_article(
                article.id, org_id, force=True
            )
        return {"articles": len(articles), "chunks": total_chunks}