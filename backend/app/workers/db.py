"""
The worker gets its own (small) async engine/session rather than
importing the API's app.db.session — it's a separate OS process/container
with its own connection pool sized for worker concurrency, not API
request concurrency.
"""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

worker_engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=5,
    max_overflow=5,
    pool_pre_ping=True,
)

WorkerSessionLocal = async_sessionmaker(
    bind=worker_engine, autoflush=False, autocommit=False, expire_on_commit=False
)


def new_worker_session() -> AsyncSession:
    return WorkerSessionLocal()
