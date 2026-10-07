"""Semantic search tests. Uses MockEmbeddingProvider."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.knowledge_search import KnowledgeSearchService
from app.services.knowledge_indexing_service import KnowledgeIndexingService

pytestmark = pytest.mark.asyncio


async def _index(db, article, org, embeddings):
    service = KnowledgeIndexingService(db=db, embeddings=embeddings)
    await service.index_article(article.id, org.id)


async def test_search_finds_relevant_chunk(
    db, make_org, make_kb_article, mock_embeddings
) -> None:
    org = await make_org()
    article = await make_kb_article(
        org=org,
        title="How to reset your password",
        body="Go to settings, click security, then reset password.",
    )
    await _index(db, article, org, mock_embeddings)

    service = KnowledgeSearchService(db=db, embeddings=mock_embeddings)
    result = await service.search(
        "reset password", org.id, top_k=3, min_similarity=0.0
    )
    assert result.total >= 1
    assert any(r.article_id == article.id for r in result.results)


async def test_search_returns_empty_when_below_threshold(
    db, make_org, make_kb_article, mock_embeddings
) -> None:
    org = await make_org()
    article = await make_kb_article(
        org=org, title="Password reset", body="Reset instructions here."
    )
    await _index(db, article, org, mock_embeddings)

    service = KnowledgeSearchService(db=db, embeddings=mock_embeddings)
    result = await service.search(
        "completely unrelated query terms",
        org.id,
        min_similarity=0.99,
    )
    assert result.total == 0


async def test_search_ignores_drafts(
    db, make_org, make_kb_article, mock_embeddings
) -> None:
    org = await make_org()
    draft = await make_kb_article(
        org=org, title="Password", body="Password password password.",
        status="DRAFT",
    )
    await _index(db, draft, org, mock_embeddings)

    service = KnowledgeSearchService(db=db, embeddings=mock_embeddings)
    result = await service.search(
        "password", org.id, min_similarity=0.0
    )
    # The draft is indexed but must not appear in search results.
    assert all(r.article_id != draft.id for r in result.results)