"""Knowledge-base RAG endpoints: search, ask, and admin reindex.

Rate limits:
- `ai:search` — semantic search, read-heavy, looser budget.
- `ai:ask`    — RAG answer generation, calls the LLM, tighter budget.
- `ai:reindex` — re-embedding job, expensive, very tight budget.

Tenant isolation is enforced at the repository/SQL layer; every endpoint
uses `user.organization_id` as the sole source of org scope. No endpoint
accepts a client-supplied organization id.
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings.factory import get_embedding_provider
from app.ai.embeddings.provider import EmbeddingProvider
from app.ai.factory import get_provider
from app.ai.knowledge_rag import KnowledgeRAGService
from app.ai.knowledge_search import KnowledgeSearchService
from app.ai.provider import LLMProvider
from app.ai.schemas import (
    KnowledgeAskRequest,
    KnowledgeAskResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
)
from app.api.dependencies.auth import get_current_user
from app.core.exceptions import ForbiddenError
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.models import User, UserRole
from app.services.knowledge_indexing_service import KnowledgeIndexingService

router = APIRouter(prefix="/ai/knowledge", tags=["ai-knowledge"])


def _require_staff(user: User) -> None:
    if user.role not in (UserRole.ADMIN, UserRole.AGENT):
        raise ForbiddenError("Only staff can use the knowledge assistant.")


def _require_admin(user: User) -> None:
    if user.role != UserRole.ADMIN:
        raise ForbiddenError("Only administrators can trigger reindexing.")


# ---------- search & ask ----------


@router.post(
    "/search",
    response_model=KnowledgeSearchResponse,
    dependencies=[Depends(rate_limit("ai:search", 60, 60))],
    summary="Semantic search across your organization's knowledge base.",
)
async def search_knowledge(
    payload: KnowledgeSearchRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    embeddings: EmbeddingProvider = Depends(get_embedding_provider),
) -> KnowledgeSearchResponse:
    _require_staff(user)
    service = KnowledgeSearchService(db=db, embeddings=embeddings)
    return await service.search(
        payload.query,
        user.organization_id,
        top_k=payload.top_k,
        min_similarity=payload.min_similarity or None,
    )


@router.post(
    "/ask",
    response_model=KnowledgeAskResponse,
    dependencies=[Depends(rate_limit("ai:ask", 20, 60))],
    summary="Answer a question grounded in your organization's knowledge base.",
)
async def ask_knowledge(
    payload: KnowledgeAskRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    embeddings: EmbeddingProvider = Depends(get_embedding_provider),
    llm: LLMProvider = Depends(get_provider),
) -> KnowledgeAskResponse:
    _require_staff(user)
    service = KnowledgeRAGService(db=db, embeddings=embeddings, llm=llm)
    return await service.ask(
        payload.query,
        user.organization_id,
        top_k=payload.top_k,
    )


# ---------- reindex (admin only) ----------


@router.post(
    "/reindex/{article_id}",
    dependencies=[Depends(rate_limit("ai:reindex", 10, 60))],
    summary="Reindex a single article (admin only).",
)
async def reindex_article(
    article_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    embeddings: EmbeddingProvider = Depends(get_embedding_provider),
) -> dict:
    _require_admin(user)
    service = KnowledgeIndexingService(db=db, embeddings=embeddings)
    chunks = await service.index_article(
        article_id, user.organization_id, force=True
    )
    await db.commit()
    return {"article_id": str(article_id), "chunks": chunks}


@router.post(
    "/reindex-all",
    dependencies=[Depends(rate_limit("ai:reindex_all", 2, 3600))],
    summary="Reindex every article in your organization (admin only).",
)
async def reindex_all(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    embeddings: EmbeddingProvider = Depends(get_embedding_provider),
) -> dict:
    _require_admin(user)
    service = KnowledgeIndexingService(db=db, embeddings=embeddings)
    result = await service.reindex_organization(user.organization_id)
    await db.commit()
    return result