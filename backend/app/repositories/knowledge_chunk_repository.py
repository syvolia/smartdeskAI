"""Tenant-scoped knowledge chunk data access, including vector search."""

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KnowledgeBaseArticle, KnowledgeChunk


class KnowledgeChunkRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def delete_for_article(
        self, article_id: uuid.UUID, org_id: uuid.UUID
    ) -> None:
        await self.db.execute(
            delete(KnowledgeChunk).where(
                KnowledgeChunk.article_id == article_id,
                KnowledgeChunk.organization_id == org_id,
            )
        )
        await self.db.flush()

    async def bulk_create(
        self,
        chunks: list[KnowledgeChunk],
    ) -> list[KnowledgeChunk]:
        if not chunks:
            return []
        self.db.add_all(chunks)
        await self.db.flush()
        return chunks

    async def count_for_article(
        self, article_id: uuid.UUID, org_id: uuid.UUID
    ) -> int:
        from sqlalchemy import func

        return int(
            await self.db.scalar(
                select(func.count())
                .select_from(KnowledgeChunk)
                .where(
                    KnowledgeChunk.article_id == article_id,
                    KnowledgeChunk.organization_id == org_id,
                )
            )
            or 0
        )

    async def search(
        self,
        org_id: uuid.UUID,
        query_vector: list[float],
        *,
        top_k: int,
        min_similarity: float,
    ) -> list[tuple[KnowledgeChunk, KnowledgeBaseArticle, float]]:
        """Cosine-similarity search restricted to a single organization.

        The organization filter is applied inside the SQL query, before
        ranking, so cross-tenant chunks are never considered candidates.
        Only PUBLISHED articles are searchable.
        """
        distance = KnowledgeChunk.embedding.cosine_distance(query_vector)
        # 1 - cosine_distance == cosine_similarity for normalized vectors.
        similarity = (1 - distance).label("similarity")

        stmt = (
            select(KnowledgeChunk, KnowledgeBaseArticle, similarity)
            .join(
                KnowledgeBaseArticle,
                KnowledgeBaseArticle.id == KnowledgeChunk.article_id,
            )
            .where(
                KnowledgeChunk.organization_id == org_id,
                KnowledgeBaseArticle.organization_id == org_id,
                KnowledgeBaseArticle.status == "PUBLISHED",
            )
            .order_by(distance.asc())
            .limit(top_k * 4)  # candidate pool; filtered by min_similarity below
        )

        rows = (await self.db.execute(stmt)).all()

        results: list[tuple[KnowledgeChunk, KnowledgeBaseArticle, float]] = []
        for chunk, article, sim in rows:
            sim_f = float(sim)
            if sim_f >= min_similarity:
                results.append((chunk, article, sim_f))
            if len(results) >= top_k:
                break
        return results