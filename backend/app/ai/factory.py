"""Provider factory and FastAPI dependency.

The provider is a process-wide singleton, chosen once at startup based on
settings. Tests override `get_ai_service` (which depends on this) via
FastAPI's dependency_overrides.
"""

from functools import lru_cache

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.provider import LLMProvider
from app.ai.providers.mock_provider import MockProvider
from app.ai.providers.openai_provider import OpenAIProvider
from app.ai.service import AIService
from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import get_db

logger = get_logger(__name__)


def _choose_provider() -> LLMProvider:
    choice = settings.ai_provider.lower()

    if choice == "mock":
        logger.info("ai_provider_selected", provider="mock", reason="forced")
        return MockProvider()

    if choice == "openai":
        if not settings.openai_api_key:
            raise RuntimeError(
                "AI_PROVIDER=openai but OPENAI_API_KEY is not set."
            )
        logger.info(
            "ai_provider_selected",
            provider="openai",
            model=settings.openai_model,
        )
        return OpenAIProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
        )

    # auto
    if settings.openai_api_key:
        logger.info(
            "ai_provider_selected",
            provider="openai",
            model=settings.openai_model,
            reason="api_key_present",
        )
        return OpenAIProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
        )

    logger.info(
        "ai_provider_selected",
        provider="mock",
        reason="no_api_key",
    )
    return MockProvider()


@lru_cache(maxsize=1)
def _provider_singleton() -> LLMProvider:
    return _choose_provider()


def get_provider() -> LLMProvider:
    """FastAPI dependency: the process-wide LLM provider."""
    return _provider_singleton()


def get_ai_service(
    db: AsyncSession = Depends(get_db),
    provider: LLMProvider = Depends(get_provider),
) -> AIService:
    """FastAPI dependency: a request-scoped AIService."""
    return AIService(db=db, provider=provider)