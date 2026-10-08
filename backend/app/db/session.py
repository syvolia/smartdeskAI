"""Async SQLAlchemy engine and session factory."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

# connect_args is passed straight through to asyncpg.connect().
#
# `statement_cache_size=0` disables asyncpg's server-side prepared
# statement cache. This is required when connecting through PgBouncer
# in transaction mode (Neon's `-pooler` endpoints, Supabase's pooler,
# etc.). Without it, asyncpg raises InvalidSQLStatementNameError under
# concurrent load because the prepared statement was cached on a
# different backend connection than the one PgBouncer hands back.
#
# The value MUST be an int. Passing it through a URL query string
# results in a string, and asyncpg compares it with `< 0`, raising
# `TypeError: '<' not supported between instances of 'str' and 'int'`.
_connect_args: dict = {"statement_cache_size": 0}

engine = create_async_engine(
    settings.database_url,
    echo=settings.app_debug,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    connect_args=_connect_args,
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a request-scoped async session."""
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def dispose_engine() -> None:
    """Dispose the engine pool on shutdown."""
    await engine.dispose()