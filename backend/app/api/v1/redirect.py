from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.redis_client import get_redis
from app.db.session import get_db_read
from app.services.cache_service import CacheService
from app.services.rate_limiter import RateLimiter
from app.services.redirect_service import RedirectService, hash_ip

router = APIRouter(tags=["redirect"])

# Short codes are base62 (alphanumeric) and aliases are alphanumeric;
# this reserved-prefix list keeps the catch-all route from swallowing
# real API paths like /api, /docs, /health.
_RESERVED_PREFIXES = {"api", "docs", "redoc", "openapi.json", "health", "favicon.ico"}


@router.get("/{code}")
async def redirect(code: str, request: Request, db: AsyncSession = Depends(get_db_read)):
    if code in _RESERVED_PREFIXES:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    client_ip = request.client.host if request.client else "unknown"
    redis_client = await get_redis()

    limiter = RateLimiter(redis_client)
    allowed, _ = await limiter.allow(
        f"ratelimit:redirect:{hash_ip(client_ip)}",
        limit=settings.RATE_LIMIT_REDIRECT_MAX,
        window_seconds=settings.RATE_LIMIT_REDIRECT_WINDOW_SECONDS,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests, slow down."
        )

    cache = CacheService(redis_client, ttl_seconds=settings.URL_CACHE_TTL_SECONDS)
    service = RedirectService(db, cache)
    target_url = await service.resolve(
        code,
        referrer=request.headers.get("referer"),
        user_agent=request.headers.get("user-agent"),
        client_ip=client_ip,
    )
    return RedirectResponse(url=target_url, status_code=status.HTTP_302_FOUND)
