"""Shared pytest fixtures.

Tests run against a dedicated PostgreSQL database (`smartdesk_test`). Each
test runs inside an outer transaction that is rolled back on teardown, and
the FastAPI app's `get_db` dependency is overridden to share that session,
so tests never leave data behind and app code sees exactly the same data
as the test.

Phase 9 additions:
- The `vector` extension is created in the test schema so `KnowledgeChunk`
  can be created alongside everything else.
- `mock_embeddings`, `mock_llm`, and `make_kb_article` fixtures support
  the RAG test suite without any network calls.
"""

import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from fakeredis.aioredis import FakeRedis
from app import models  # noqa: F401  -- registers all models on Base.metadata
from app.ai.embeddings.mock_embedding import MockEmbeddingProvider
from app.ai.providers.mock_provider import MockProvider
from app.api.dependencies.auth import (
    get_current_user,
    require_admin,
    require_agent,
    require_customer,
)
from app.core.config import settings
from app.core.security import (
    create_access_token,
    hash_password,
)
from app.db.base import Base
from app.db.session import get_db
from app.main import app as fastapi_app
from app.models import (
    ArticleStatus,
    Customer,
    KnowledgeBaseArticle,
    KnowledgeBaseCategory,
    Organization,
    Ticket,
    User,
    UserRole,
)

TEST_DB_NAME = "smartdesk_test"


# ---------------- DB URLs ----------------


def _admin_url() -> str:
    return (
        f"postgresql+psycopg2://{settings.postgres_user}:{settings.postgres_password}"
        f"@{settings.postgres_host}:{settings.postgres_port}/postgres"
    )


def _test_sync_url() -> str:
    return (
        f"postgresql+psycopg2://{settings.postgres_user}:{settings.postgres_password}"
        f"@{settings.postgres_host}:{settings.postgres_port}/{TEST_DB_NAME}"
    )


def _test_async_url() -> str:
    return (
        f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}"
        f"@{settings.postgres_host}:{settings.postgres_port}/{TEST_DB_NAME}"
    )


# ---------------- Database lifecycle ----------------


@pytest.fixture(scope="session", autouse=True)
def _create_test_database() -> None:
    admin = create_engine(_admin_url(), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": TEST_DB_NAME},
        ).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{TEST_DB_NAME}"'))
    admin.dispose()
    yield


@pytest_asyncio.fixture(scope="session")
async def engine(_create_test_database):
    """Session-scoped engine with a clean schema.

    We drop and recreate the `public` schema rather than individual tables
    so that native enum types (user_role, ticket_status, ...) and the
    pgvector extension are fully rebuilt with the current Python definitions.
    """
    eng = create_async_engine(_test_async_url(), future=True)
    async with eng.begin() as conn:
        await conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield eng
    finally:
        await eng.dispose()


@pytest_asyncio.fixture
async def db(engine) -> AsyncGenerator[AsyncSession, None]:
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(
        bind=connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    try:
        yield session
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()


# ---------------- HTTP clients ----------------


@pytest_asyncio.fixture
async def app_with_db(db: AsyncSession) -> AsyncGenerator[FastAPI, None]:
    async def override_get_db():
        yield db

    fastapi_app.dependency_overrides[get_db] = override_get_db
    try:
        yield fastapi_app
    finally:
        fastapi_app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(app_with_db: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app_with_db)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

@pytest_asyncio.fixture
async def mock_redis():
    """In-memory Redis for tests that exercise caching and dedupe."""
    client = FakeRedis(decode_responses=True)
    try:
        yield client
    finally:
        await client.aclose()
# ---------------- Test-only scope app ----------------


def _build_scope_app() -> FastAPI:
    """Minimal app exposing dependency-gated routes.

    These routes are the same pattern that production endpoints use, so
    they exercise the real authorization layer without needing business
    endpoints to exist yet.
    """
    scope = FastAPI()

    @scope.get("/test/me")
    async def test_me(user: User = Depends(get_current_user)) -> dict:
        return {
            "user_id": str(user.id),
            "org_id": str(user.organization_id),
            "role": user.role.value,
        }

    @scope.get("/test/admin")
    async def test_admin(user: User = Depends(require_admin)) -> dict:
        return {"ok": True}

    @scope.get("/test/agent")
    async def test_agent(user: User = Depends(require_agent)) -> dict:
        return {"ok": True}

    @scope.get("/test/customer")
    async def test_customer(user: User = Depends(require_customer)) -> dict:
        return {"ok": True}

    @scope.get("/test/org-customers")
    async def test_org_customers(
        user: User = Depends(require_agent),
        session: AsyncSession = Depends(get_db),
    ) -> list[str]:
        result = await session.execute(
            select(Customer).where(Customer.organization_id == user.organization_id)
        )
        return [str(c.id) for c in result.scalars().all()]

    @scope.get("/test/org-tickets")
    async def test_org_tickets(
        user: User = Depends(require_agent),
        session: AsyncSession = Depends(get_db),
    ) -> list[str]:
        result = await session.execute(
            select(Ticket).where(Ticket.organization_id == user.organization_id)
        )
        return [str(t.id) for t in result.scalars().all()]

    return scope


@pytest_asyncio.fixture
async def scope_client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db

    scope = _build_scope_app()
    scope.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=scope)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c
    finally:
        scope.dependency_overrides.clear()


# ---------------- Data factories ----------------


@pytest_asyncio.fixture
async def make_org(db: AsyncSession):
    async def _make(
        *,
        name: str | None = None,
        slug: str | None = None,
    ) -> Organization:
        suffix = uuid.uuid4().hex[:8]
        org = Organization(
            name=name or f"Org {suffix}",
            slug=slug or f"org-{suffix}",
        )
        db.add(org)
        await db.flush()
        return org

    return _make


@pytest_asyncio.fixture
async def make_user(db: AsyncSession):
    async def _make(
        *,
        org: Organization,
        email: str | None = None,
        role: UserRole = UserRole.AGENT,
        password: str = "Passw0rd!",
        full_name: str = "Test User",
        is_active: bool = True,
    ) -> tuple[User, str]:
        user = User(
            organization_id=org.id,
            email=email or f"user-{uuid.uuid4().hex[:8]}@example.test",
            full_name=full_name,
            hashed_password=hash_password(password),
            role=role,
            is_active=is_active,
        )
        db.add(user)
        await db.flush()
        return user, password

    return _make


@pytest_asyncio.fixture
async def make_customer(db: AsyncSession):
    async def _make(
        *,
        org: Organization,
        email: str | None = None,
        full_name: str = "Test Customer",
    ) -> Customer:
        customer = Customer(
            organization_id=org.id,
            email=email or f"cust-{uuid.uuid4().hex[:8]}@example.test",
            full_name=full_name,
        )
        db.add(customer)
        await db.flush()
        return customer

    return _make


@pytest_asyncio.fixture
async def make_ticket(db: AsyncSession):
    async def _make(
        *,
        org: Organization,
        customer: Customer,
        title: str = "Test ticket",
        description: str = "...",
    ) -> Ticket:
        ticket = Ticket(
            organization_id=org.id,
            customer_id=customer.id,
            title=title,
            description=description,
        )
        db.add(ticket)
        await db.flush()
        return ticket

    return _make


# ---------------- Auth helpers ----------------


@pytest.fixture
def auth_header():
    """Build an Authorization header from an arbitrary access token."""
    def _header(token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    return _header


@pytest.fixture
def make_expired_access_token():
    """Issue an access token that has already expired, signed properly."""
    import jwt

    def _make(user_id: uuid.UUID, *, ago_seconds: int = 3600) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user_id),
            "type": "access",
            "iat": int((now.timestamp()) - ago_seconds - 60),
            "exp": int((now.timestamp()) - ago_seconds),
        }
        return jwt.encode(
            payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
        )

    return _make


@pytest.fixture
def make_valid_access_token():
    """Issue a properly signed, non-expired access token for a user id."""
    def _make(user_id: uuid.UUID) -> str:
        token, _ = create_access_token(user_id)
        return token

    return _make


# ---------------- Phase 9: AI / embeddings / knowledge base ----------------


@pytest.fixture
def mock_embeddings() -> MockEmbeddingProvider:
    """Deterministic embedding provider. No network, no API key."""
    return MockEmbeddingProvider(dimension=settings.embedding_dimension)


@pytest.fixture
def mock_llm() -> MockProvider:
    """Deterministic LLM provider. No network, no API key."""
    return MockProvider()


@pytest_asyncio.fixture
async def make_kb_article(db: AsyncSession):
    """Create a KnowledgeBaseArticle with a unique slug.

    Defaults to PUBLISHED status because most RAG tests need articles that
    are actually searchable.
    """
    async def _make(
        *,
        org: Organization,
        title: str,
        body: str,
        status: str = "PUBLISHED",
        category: KnowledgeBaseCategory | None = None,
    ) -> KnowledgeBaseArticle:
        slug_base = title.lower().replace(" ", "-")[:60]
        slug = f"{slug_base}-{uuid.uuid4().hex[:6]}"
        article = KnowledgeBaseArticle(
            organization_id=org.id,
            category_id=category.id if category else None,
            title=title,
            slug=slug,
            body=body,
            status=ArticleStatus(status),
        )
        db.add(article)
        await db.flush()
        return article

    return _make