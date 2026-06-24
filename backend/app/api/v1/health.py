from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.redis_client import get_redis
from app.db.session import engine, get_db
from app.schemas.analytics import SystemMetricsResponse
from app.services.cache_service import CacheService
from app.services.system_metrics_service import SystemMetricsService

router = APIRouter(tags=["architecture"])


@router.get("/architecture/metrics", response_model=SystemMetricsResponse)
async def system_metrics():
    redis_client = await get_redis()
    cache_service = CacheService(redis_client)
    service = SystemMetricsService(redis_client, cache_service, engine)
    return await service.get_metrics()


@router.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    checks = {"database": "down", "redis": "down"}

    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "up"
    except Exception:
        pass

    try:
        redis_client = await get_redis()
        await redis_client.ping()
        checks["redis"] = "up"
    except Exception:
        pass

    overall = "healthy" if all(v == "up" for v in checks.values()) else "degraded"
    return {"status": overall, "checks": checks}


@router.get("/health/live")
async def liveness():
    """Liveness probe — process is up and serving requests. No dependency checks."""
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness(db: AsyncSession = Depends(get_db)):
    """Readiness probe — can this replica actually serve traffic right now."""
    await db.execute(text("SELECT 1"))
    redis_client = await get_redis()
    await redis_client.ping()
    return {"status": "ready"}
