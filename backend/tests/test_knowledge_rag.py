"""RAG /ask behavior: grounding, refusal, and citations."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.knowledge_rag import KnowledgeRAGService
from app.ai.schemas import RAGAnswer
from app.services.knowledge_indexing_service import KnowledgeIndexingService

pytestmark = pytest.mark.asyncio


async def test_ask_returns_grounded_answer_with_citations(
    db, make_org, make_kb_article, mock_embeddings, mock_llm
) -> None:
    org = await make_org()
    article = await make_kb_article(
        org=org,
        title="Resetting your password",
        body="Navigate to settings, then security, then reset password.",
    )
    await KnowledgeIndexingService(db=db, embeddings=mock_embeddings).index_article(
        article.id, org.id
    )

    mock_llm.set_response(
        RAGAnswer,
        RAGAnswer(
            answer="Go to settings → security → reset password [1].",
            cited_source_numbers=[1],
            is_grounded=True,
            confidence=0.85,
        ),
    )

    service = KnowledgeRAGService(
        db=db, embeddings=mock_embeddings, llm=mock_llm
    )
    result = await service.ask("How do I reset my password?", org.id)

    assert result.is_grounded is True
    assert result.citations
    assert result.citations[0].article_id == article.id
    assert "[1]" in result.answer


async def test_ask_returns_not_grounded_when_no_chunks(
    db, make_org, mock_embeddings, mock_llm
) -> None:
    org = await make_org()

    service = KnowledgeRAGService(
        db=db, embeddings=mock_embeddings, llm=mock_llm
    )
    result = await service.ask("unrelated question", org.id)

    assert result.is_grounded is False
    assert result.citations == []
    assert result.used_chunks == 0
    assert result.no_evidence_reason == "no_relevant_chunks"
    # LLM should never have been called.
    assert mock_llm.calls == []


async def test_ask_downgrades_ungrounded_llm_output(
    db, make_org, make_kb_article, mock_embeddings, mock_llm
) -> None:
    org = await make_org()
    article = await make_kb_article(
        org=org, title="Topic", body="Topic content here."
    )
    await KnowledgeIndexingService(db=db, embeddings=mock_embeddings).index_article(
        article.id, org.id
    )

    mock_llm.set_response(
        RAGAnswer,
        RAGAnswer(
            answer="I don't know.",
            cited_source_numbers=[],
            is_grounded=False,
            confidence=0.1,
        ),
    )

    service = KnowledgeRAGService(
        db=db, embeddings=mock_embeddings, llm=mock_llm
    )
    result = await service.ask("some question", org.id)
    assert result.is_grounded is False
    assert result.citations == []


async def test_ask_filters_hallucinated_citation_numbers(
    db, make_org, make_kb_article, mock_embeddings, mock_llm
) -> None:
    org = await make_org()
    article = await make_kb_article(
        org=org, title="Topic", body="Topic content."
    )
    await KnowledgeIndexingService(db=db, embeddings=mock_embeddings).index_article(
        article.id, org.id
    )

    mock_llm.set_response(
        RAGAnswer,
        RAGAnswer(
            answer="Answer [99].",
            cited_source_numbers=[99],  # not in range
            is_grounded=True,
            confidence=0.9,
        ),
    )

    service = KnowledgeRAGService(
        db=db, embeddings=mock_embeddings, llm=mock_llm
    )
    result = await service.ask("anything", org.id)
    # Hallucinated citation removed → no citations → not grounded.
    assert result.citations == []
    assert result.is_grounded is False