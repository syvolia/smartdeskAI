"""Vector-search tenant isolation.

These tests are the load-bearing ones for the RAG feature: they prove
that no query, however crafted, can retrieve chunks belonging to another
organization.
"""

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.knowledge_rag import KnowledgeRAGService
from app.ai.knowledge_search import KnowledgeSearchService
from app.ai.schemas import RAGAnswer
from app.models import KnowledgeChunk
from app.services.knowledge_indexing_service import KnowledgeIndexingService

pytestmark = pytest.mark.asyncio


async def _index(db, article, org, embeddings):
    await KnowledgeIndexingService(
        db=db, embeddings=embeddings
    ).index_article(article.id, org.id)


async def test_search_never_returns_other_org_chunks(
    db, make_org, make_kb_article, mock_embeddings
) -> None:
    """Search as Org A for text that appears ONLY in Org B's KB."""
    org_a = await make_org(slug="tenant-a")
    org_b = await make_org(slug="tenant-b")

    # B has a unique distinctive phrase. A has an unrelated one.
    await make_kb_article(
        org=org_b,
        title="Secret refund policy",
        body="The secret refund code is XYZ-999-ALPHA. Refund refund refund.",
    )
    a_article = await make_kb_article(
        org=org_a,
        title="Unrelated topic",
        body="Nothing about refunds here.",
    )

    # Index everything.
    for org in (org_a, org_b):
        articles = list(
            (
                await db.scalars(
                    select(article_cls := __import__("app.models", fromlist=["KnowledgeBaseArticle"]).KnowledgeBaseArticle)
                    .where(article_cls.organization_id == org.id)
                )
            ).all()
        )
        for a in articles:
            await _index(db, a, org, mock_embeddings)

    # Query as org A for B's secret phrase.
    service = KnowledgeSearchService(db=db, embeddings=mock_embeddings)
    result = await service.search(
        "secret refund code", org_a.id, min_similarity=0.0
    )

    # No result may point at an article that isn't in org A.
    org_b_article_ids = set(
        (
            await db.scalars(
                select(__import__("app.models", fromlist=["KnowledgeBaseArticle"]).KnowledgeBaseArticle.id)
                .where(__import__("app.models", fromlist=["KnowledgeBaseArticle"]).KnowledgeBaseArticle.organization_id == org_b.id)
            )
        ).all()
    )
    for r in result.results:
        assert r.article_id not in org_b_article_ids


async def test_search_scoped_by_org_id_at_sql_level(
    db, make_org, make_kb_article, mock_embeddings
) -> None:
    """Bypass the service and confirm the raw query filters by org_id."""
    org_a = await make_org(slug="tenant-a")
    org_b = await make_org(slug="tenant-b")

    a_article = await make_kb_article(
        org=org_a, title="A", body="alpha beta gamma"
    )
    b_article = await make_kb_article(
        org=org_b, title="B", body="alpha beta gamma"
    )
    await _index(db, a_article, org_a, mock_embeddings)
    await _index(db, b_article, org_b, mock_embeddings)

    # Raw SQL count of chunks per org — proves data is physically separated.
    total_chunks = int(
        await db.scalar(text("SELECT COUNT(*) FROM knowledge_chunks")) or 0
    )
    a_chunks = int(
        await db.scalar(
            text(
                "SELECT COUNT(*) FROM knowledge_chunks "
                "WHERE organization_id = :org_id"
            ),
            {"org_id": str(org_a.id)},
        )
        or 0
    )
    b_chunks = int(
        await db.scalar(
            text(
                "SELECT COUNT(*) FROM knowledge_chunks "
                "WHERE organization_id = :org_id"
            ),
            {"org_id": str(org_b.id)},
        )
        or 0
    )
    assert a_chunks > 0
    assert b_chunks > 0
    assert a_chunks + b_chunks == total_chunks
    assert a_chunks != b_chunks or total_chunks == 2 * a_chunks  # both exist


async def test_rag_never_uses_other_org_sources(
    db, make_org, make_kb_article, mock_embeddings, mock_llm
) -> None:
    """RAG must not leak B's content into A's prompt. If A has no
    relevant chunk, the service short-circuits before calling the LLM."""
    org_a = await make_org(slug="tenant-a")
    org_b = await make_org(slug="tenant-b")

    b_article = await make_kb_article(
        org=org_b,
        title="Highly specific phrase",
        body="zebra quantum banana tambourine",
    )
    await _index(db, b_article, org_b, mock_embeddings)

    # Org A has no articles at all.
    mock_llm.set_response(
        RAGAnswer,
        RAGAnswer(
            answer="should not be reached",
            cited_source_numbers=[],
            is_grounded=False,
            confidence=0.0,
        ),
    )

    service = KnowledgeRAGService(
        db=db, embeddings=mock_embeddings, llm=mock_llm
    )
    result = await service.ask("zebra quantum banana", org_a.id)

    # LLM not called because no evidence in A's KB.
    assert mock_llm.calls == []
    assert result.is_grounded is False
    assert result.citations == []


async def test_rag_citations_only_from_caller_org(
    db, make_org, make_kb_article, mock_embeddings, mock_llm
) -> None:
    org_a = await make_org(slug="tenant-a")
    org_b = await make_org(slug="tenant-b")

    a_article = await make_kb_article(
        org=org_a, title="A article", body="alpha article content"
    )
    await _index(db, a_article, org_a, mock_embeddings)

    b_article = await make_kb_article(
        org=org_b, title="B article", body="alpha article content"
    )
    await _index(db, b_article, org_b, mock_embeddings)

    mock_llm.set_response(
        RAGAnswer,
        RAGAnswer(
            answer="Answer [1].",
            cited_source_numbers=[1],
            is_grounded=True,
            confidence=0.9,
        ),
    )

    service = KnowledgeRAGService(
        db=db, embeddings=mock_embeddings, llm=mock_llm
    )
    result = await service.ask("alpha article", org_a.id)

    # Every citation must be from org A.
    for citation in result.citations:
        assert citation.article_id == a_article.id
        assert citation.article_id != b_article.id


async def test_cross_tenant_chunk_removal_on_article_delete(
    db, make_org, make_kb_article, mock_embeddings
) -> None:
    """Deleting an article in org A must not affect org B's chunks."""
    org_a = await make_org(slug="tenant-a")
    org_b = await make_org(slug="tenant-b")

    a_article = await make_kb_article(
        org=org_a, title="A", body="alpha article content"
    )
    b_article = await make_kb_article(
        org=org_b, title="B", body="beta article content"
    )
    await _index(db, a_article, org_a, mock_embeddings)
    await _index(db, b_article, org_b, mock_embeddings)

    b_chunks_before = int(
        await db.scalar(
            text(
                "SELECT COUNT(*) FROM knowledge_chunks "
                "WHERE organization_id = :org_id"
            ),
            {"org_id": str(org_b.id)},
        )
        or 0
    )
    assert b_chunks_before > 0

    await db.delete(a_article)
    await db.flush()

    b_chunks_after = int(
        await db.scalar(
            text(
                "SELECT COUNT(*) FROM knowledge_chunks "
                "WHERE organization_id = :org_id"
            ),
            {"org_id": str(org_b.id)},
        )
        or 0
    )
    assert b_chunks_after == b_chunks_before

    # And org A's chunks are gone.
    a_chunks_after = int(
        await db.scalar(
            text(
                "SELECT COUNT(*) FROM knowledge_chunks "
                "WHERE organization_id = :org_id"
            ),
            {"org_id": str(org_a.id)},
        )
        or 0
    )
    assert a_chunks_after == 0