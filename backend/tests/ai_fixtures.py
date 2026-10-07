"""Reusable fixtures for AI tests.

Tests must never hit OpenAI. The `mock_provider` fixture replaces the
process-wide provider with a deterministic MockProvider, and
`ai_client` wires it into the FastAPI app via dependency overrides.
"""

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.factory import get_ai_service
from app.ai.providers.mock_provider import MockProvider
from app.ai.service import AIService
from app.db.session import get_db
from app.main import app as fastapi_app


@pytest.fixture
def mock_provider() -> MockProvider:
    return MockProvider()


@pytest_asyncio.fixture
async def ai_client(
    db: AsyncSession, mock_provider: MockProvider
) -> AsyncGenerator[tuple[AsyncClient, MockProvider], None]:
    async def override_get_db():
        yield db

    def override_ai_service(
        session: AsyncSession = None,  # type: ignore[assignment]
    ) -> AIService:
        return AIService(db=db, provider=mock_provider)

    fastapi_app.dependency_overrides[get_db] = override_get_db
    fastapi_app.dependency_overrides[get_ai_service] = override_ai_service
    try:
        transport = ASGITransport(app=fastapi_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c, mock_provider
    finally:
        fastapi_app.dependency_overrides.clear()