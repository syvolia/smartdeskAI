"""Embedding provider factory and FastAPI dependencies."""

from functools import lru_cache

from fastapi import Depends

from app.ai.embeddings.mock_embedding import MockEmbeddingProvider
from app.ai.embeddings.openai_embedding import OpenAIEmbeddingProvider
from app.ai.embeddings.provider import EmbeddingProvider
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def _choose_provider() -> EmbeddingProvider:
    choice = settings.embedding_provider.lower()

    if choice == "mock":
        logger.info("embedding_provider_selected", provider="mock", reason="forced")
        return MockEmbeddingProvider(dimension=settings.embedding_dimension)

    if choice == "openai":
        if not settings.openai_api_key:
            raise RuntimeError(
                "EMBEDDING_PROVIDER=openai but OPENAI_API_KEY is not set."
            )
        logger.info(
            "embedding_provider_selected",
            provider="openai",
            model=settings.openai_embedding_model,
        )
        return OpenAIEmbeddingProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_embedding_model,
            dimension=settings.embedding_dimension,
        )

    if settings.openai_api_key:
        logger.info(
            "embedding_provider_selected",
            provider="openai",
            model=settings.openai_embedding_model,
            reason="api_key_present",
        )
        return OpenAIEmbeddingProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_embedding_model,
            dimension=settings.embedding_dimension,
        )

    logger.info(
        "embedding_provider_selected", provider="mock", reason="no_api_key"
    )
    return MockEmbeddingProvider(dimension=settings.embedding_dimension)


@lru_cache(maxsize=1)
def _embedding_singleton() -> EmbeddingProvider:
    return _choose_provider()


def get_embedding_provider() -> EmbeddingProvider:
    """FastAPI dependency: process-wide embedding provider."""
    return _embedding_singleton()