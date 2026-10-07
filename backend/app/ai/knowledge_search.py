"""Semantic search over an organization's knowledge base."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings.provider import EmbeddingProvider
from app.ai.schemas import KnowledgeChunkMatch, KnowledgeSearchResponse
from app.core.config import settings
from app.repositories.knowledge_chunk_repository import (
    KnowledgeChunkRepository,
)


class KnowledgeSearchService:
    def __init__(
        self,
        db: AsyncSession,
        embeddings: EmbeddingProvider,
    ) -> None:
        self.db = db
        self.embeddings = embeddings
        self.repo = KnowledgeChunkRepository(db)

    async def search(
        self,
        query: str,
        org_id: uuid.UUID,
        *,
        top_k: int | None = None,
        min_similarity: float | None = None,
    ) -> KnowledgeSearchResponse:
        top_k = top_k or settings.knowledge_search_default_top_k
        min_similarity = (
            min_similarity
            if min_similarity is not None
            else settings.knowledge_search_min_similarity
        )

        vectors, _ = await self.embeddings.embed(
            [query],
            timeout_seconds=settings.openai_timeout_seconds,
        )
        query_vector = vectors[0]

        rows = await self.repo.search(
            org_id,
            query_vector,
            top_k=top_k,
            min_similarity=min_similarity,
        )

        results = [
            KnowledgeChunkMatch(
                chunk_id=chunk.id,
                article_id=article.id,
                article_title=article.title,
                article_slug=article.slug,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                similarity=round(sim, 4),
            )
            for chunk, article, sim in rows
        ]

        return KnowledgeSearchResponse(
            query=query,
            results=results,
            total=len(results),
            min_similarity_used=min_similarity,
        )