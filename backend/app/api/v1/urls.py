from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.redis_client import get_redis
from app.db.session import get_db, get_db_read
from app.models.user import User
from app.schemas.url import URLCreate, URLListResponse, URLRead, URLUpdate
from app.services.cache_service import CacheService
from app.services.rate_limiter import RateLimiter
from app.services.url_service import URLService

router = APIRouter(prefix="/urls", tags=["urls"])


@router.post("", response_model=URLRead, status_code=status.HTTP_201_CREATED)
async def create_url(
    payload: URLCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    redis_client = await get_redis()
    limiter = RateLimiter(redis_client)
    allowed, remaining = await limiter.allow(
        f"ratelimit:create:{current_user.id}",
        limit=settings.RATE_LIMIT_CREATE_MAX,
        window_seconds=settings.RATE_LIMIT_CREATE_WINDOW_SECONDS,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded for URL creation. Try again shortly.",
        )

    cache = CacheService(redis_client, ttl_seconds=settings.URL_CACHE_TTL_SECONDS)
    service = URLService(db, cache)
    url = await service.create(current_user.id, payload)
    return url


@router.get("", response_model=URLListResponse)
async def list_urls(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: str | None = Query(None, max_length=255),
    is_active: bool | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_read),
):
    redis_client = await get_redis()
    cache = CacheService(redis_client, ttl_seconds=settings.URL_CACHE_TTL_SECONDS)
    service = URLService(db, cache)
    return await service.list_for_owner(
        current_user.id, page=page, page_size=page_size, search=search, is_active=is_active
    )


@router.get("/{url_id}", response_model=URLRead)
async def get_url(
    url_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_read),
):
    redis_client = await get_redis()
    cache = CacheService(redis_client, ttl_seconds=settings.URL_CACHE_TTL_SECONDS)
    service = URLService(db, cache)
    url = await service.get_owned(current_user.id, url_id)
    return service._to_read(url)


@router.patch("/{url_id}", response_model=URLRead)
async def update_url(
    url_id: int,
    payload: URLUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    redis_client = await get_redis()
    cache = CacheService(redis_client, ttl_seconds=settings.URL_CACHE_TTL_SECONDS)
    service = URLService(db, cache)
    return await service.update(current_user.id, url_id, payload)


@router.delete("/{url_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_url(
    url_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    redis_client = await get_redis()
    cache = CacheService(redis_client, ttl_seconds=settings.URL_CACHE_TTL_SECONDS)
    service = URLService(db, cache)
    await service.delete(current_user.id, url_id)
