"""Async SQLAlchemy engine and session factory."""

from collections.abc import AsyncGenerator
from uuid import uuid4

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import settings

# connect_args is passed straight through to asyncpg.connect().
#
# 1. `statement_cache_size=0` disables asyncpg's server-side prepared
#    statement cache. Required for PgBouncer transaction mode.
#
# 2. `prepared_statement_name_func` gives every prepared statement a
#    unique name. Without this, SQLAlchemy's internal `__asyncpg_stmt_N__`
#    names collide when multiple queries run on the same pooled
#    connection — leading to intermittent
#    `asyncpg.exceptions.InvalidSQLStatementNameError: prepared statement
#    "__asyncpg_stmt_XX__" does not exist`. This is the documented
#    SQLAlchemy fix for PgBouncer / Neon pooler compatibility.
#
# Both values MUST be ints and callables respectively. Passing them via
# a URL query string converts them to strings and breaks asyncpg.
_connect_args: dict = {
    "statement_cache_size": 0,
    "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__",
}

# NullPool: no client-side connection reuse.
#
# On a managed Postgres with its own connection pooler (Neon, Supabase),
# running a client-side pool on top of a server-side pooler causes
# stale-connection bugs and exceeds the pooler's connection cap under
# load. NullPool opens and closes a connection per request — more
# connection churn, but the pooler handles the actual pooling.
#
# For a self-hosted Postgres without a pooler, switch back to
# pool_size=5, max_overflow=10 and drop NullPool. The connect_args above
# still apply.
engine = create_async_engine(
    settings.database_url,
    echo=settings.app_debug,
    poolclass=NullPool,
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