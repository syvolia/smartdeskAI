"""Embedding pipeline tests using the mock embedding provider."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.chunking import chunk_content, clean_content
from app.models import KnowledgeChunk
from app.services.knowledge_indexing_service import KnowledgeIndexingService

pytestmark = pytest.mark.asyncio


def test_clean_content_normalizes_whitespace() -> None:
    assert clean_content("a   b\n\n\n\nc") == "a b\n\nc"


def test_chunk_content_splits_long_text() -> None:
    para = "Sentence. " * 400
    chunks = chunk_content(para, target_tokens=200, overlap_tokens=0)
    assert len(chunks) > 1
    assert all(len(c) > 0 for c in chunks)


async def test_index_article_creates_chunks(
    db: AsyncSession, make_org, make_kb_article, mock_embeddings
) -> None:
    org = await make_org()
    article = await make_kb_article(
        org=org,
        title="Reset password",
        body="Step one. " * 200,
    )

    service = KnowledgeIndexingService(db=db, embeddings=mock_embeddings)
    chunks_created = await service.index_article(article.id, org.id)

    assert chunks_created > 0
    rows = list(
        (
            await db.scalars(
                select(KnowledgeChunk).where(
                    KnowledgeChunk.article_id == article.id
                )
            )
        ).all()
    )
    assert len(rows) == chunks_created
    assert all(r.organization_id == org.id for r in rows)
    assert all(len(r.embedding) == mock_embeddings.dimension for r in rows)


async def test_reindex_unchanged_content_is_noop(
    db: AsyncSession, make_org, make_kb_article, mock_embeddings
) -> None:
    org = await make_org()
    article = await make_kb_article(org=org, title="Foo", body="Bar baz qux.")

    service = KnowledgeIndexingService(db=db, embeddings=mock_embeddings)
    first = await service.index_article(article.id, org.id)
    second = await service.index_article(article.id, org.id)
    assert first == second  # no-op because content unchanged


async def test_reindex_replaces_chunks(
    db: AsyncSession, make_org, make_kb_article, mock_embeddings
) -> None:
    org = await make_org()
    article = await make_kb_article(org=org, title="Foo", body="Short body.")

    service = KnowledgeIndexingService(db=db, embeddings=mock_embeddings)
    await service.index_article(article.id, org.id)

    article.body = "Much longer body. " * 300
    await db.flush()

    await service.index_article(article.id, org.id, force=True)

    rows = list(
        (
            await db.scalars(
                select(KnowledgeChunk).where(
                    KnowledgeChunk.article_id == article.id
                )
            )
        ).all()
    )
    assert len(rows) > 1  # content was long enough for multiple chunks


async def test_index_is_tenant_scoped(
    db: AsyncSession, make_org, make_kb_article, mock_embeddings
) -> None:
    from app.core.exceptions import NotFoundError

    org_a = await make_org(slug="tenant-a")
    org_b = await make_org(slug="tenant-b")
    article = await make_kb_article(org=org_a, title="A", body="Body A.")

    service = KnowledgeIndexingService(db=db, embeddings=mock_embeddings)
    with pytest.raises(NotFoundError):
        await service.index_article(article.id, org_b.id)