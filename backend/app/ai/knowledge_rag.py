"""Grounded question answering over the knowledge base.

The model receives only retrieved chunks from the caller's organization.
If retrieval returns nothing above the similarity threshold, the service
short-circuits and returns a "not enough evidence" response instead of
calling the LLM — no hallucination when the KB doesn't cover the query.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings.provider import EmbeddingProvider
from app.ai.provider import LLMProvider
from app.ai.schemas import (
    KnowledgeAskResponse,
    KnowledgeCitation,
    RAGAnswer,
)
from app.core.config import settings
from app.core.logging import get_logger
from app.repositories.knowledge_chunk_repository import (
    KnowledgeChunkRepository,
)

logger = get_logger(__name__)

SYSTEM_RAG = (
    "You answer support questions using ONLY the sources provided. "
    "Cite sources inline as [1], [2], matching the numbers in the Sources "
    "block. If the sources do not contain enough information to answer, "
    "set is_grounded=false and answer with a short statement that the "
    "knowledge base doesn't cover the question. Never invent facts, "
    "timelines, or article titles. Never cite a source number you were "
    "not given."
)

NOT_ENOUGH_EVIDENCE = (
    "I don't have enough information in the knowledge base to answer this. "
    "Consider creating an article or asking a subject-matter expert."
)


class KnowledgeRAGService:
    def __init__(
        self,
        db: AsyncSession,
        embeddings: EmbeddingProvider,
        llm: LLMProvider,
    ) -> None:
        self.db = db
        self.embeddings = embeddings
        self.llm = llm
        self.chunks = KnowledgeChunkRepository(db)

    async def ask(
        self,
        query: str,
        org_id: uuid.UUID,
        *,
        top_k: int | None = None,
    ) -> KnowledgeAskResponse:
        top_k = top_k or settings.knowledge_search_default_top_k

        vectors, _ = await self.embeddings.embed(
            [query],
            timeout_seconds=settings.openai_timeout_seconds,
        )
        query_vector = vectors[0]

        rows = await self.chunks.search(
            org_id,
            query_vector,
            top_k=top_k,
            min_similarity=settings.knowledge_rag_min_similarity,
        )

        if not rows:
            logger.info(
                "rag_no_evidence",
                org_id=str(org_id),
                query_len=len(query),
            )
            return KnowledgeAskResponse(
                query=query,
                answer=NOT_ENOUGH_EVIDENCE,
                is_grounded=False,
                confidence=None,
                citations=[],
                used_chunks=0,
                no_evidence_reason="no_relevant_chunks",
            )

        # Build a numbered sources block. Numbers are 1-based and stable
        # for the duration of this call.
        sources_lines: list[str] = []
        source_lookup: dict[int, tuple] = {}
        for idx, (chunk, article, _sim) in enumerate(rows, start=1):
            source_lookup[idx] = (chunk, article)
            sources_lines.append(
                f"[{idx}] {article.title}\n{chunk.content}"
            )
        sources_block = "\n\n".join(sources_lines)

        user_prompt = (
            f"Sources:\n{sources_block}\n\n"
            f"Question: {query}\n\n"
            "Answer using only the sources above. Cite as [n]. If the "
            "sources don't answer the question, set is_grounded to false "
            "and say so explicitly."
        )

        result, meta = await self.llm.complete_json(
            system=SYSTEM_RAG,
            user=user_prompt,
            schema=RAGAnswer,
            timeout_seconds=settings.openai_timeout_seconds,
        )

        # Validate citations against the actual retrieved sources.
        valid_numbers = set(source_lookup.keys())
        valid_citations = sorted(
            n for n in result.cited_source_numbers if n in valid_numbers
        )

        citations: list[KnowledgeCitation] = []
        for n in valid_citations:
            chunk, article = source_lookup[n]
            excerpt = chunk.content[:240].replace("\n", " ")
            citations.append(
                KnowledgeCitation(
                    source_number=n,
                    article_id=article.id,
                    article_title=article.title,
                    article_slug=article.slug,
                    chunk_id=chunk.id,
                    excerpt=excerpt,
                )
            )

        # If the model claims to be grounded but cites nothing, distrust it.
        is_grounded = bool(result.is_grounded and citations)

        logger.info(
            "rag_answered",
            org_id=str(org_id),
            used_chunks=len(rows),
            citations=len(citations),
            is_grounded=is_grounded,
            model=meta.model,
            latency_ms=meta.latency_ms,
        )

        return KnowledgeAskResponse(
            query=query,
            answer=result.answer,
            is_grounded=is_grounded,
            confidence=result.confidence,
            citations=citations,
            used_chunks=len(rows),
            no_evidence_reason=None if is_grounded else "insufficient_evidence",
        )