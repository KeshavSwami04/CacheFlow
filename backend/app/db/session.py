"""
Async SQLAlchemy engine + session factory.

Pool size is configurable per-replica via env (DB_POOL_SIZE /
DB_MAX_OVERFLOW) — with N stateless API replicas behind a load balancer,
total Postgres connections ≈ N * (pool_size + max_overflow), which is the
number you size `max_connections` / pgbouncer against when scaling out.
"""
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=True,
    echo=False,
)

engine_replica = create_async_engine(
    settings.DATABASE_REPLICA_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=True,
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)

AsyncSessionLocalReplica = async_sessionmaker(
    bind=engine_replica,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a request-scoped primary/write DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


get_db_write = get_db


async def get_db_read() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a request-scoped replica/read DB session."""
    async with AsyncSessionLocalReplica() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
