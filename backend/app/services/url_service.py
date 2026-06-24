import math
import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.url import URL
from app.repositories.url_repository import URLRepository
from app.schemas.url import URLCreate, URLListResponse, URLRead, URLUpdate
from app.services.cache_service import CacheService


class URLService:
    def __init__(self, db: AsyncSession, cache: CacheService):
        self.repo = URLRepository(db)
        self.cache = cache

    async def create(self, owner_id: uuid.UUID, payload: URLCreate) -> URLRead:
        if payload.custom_alias and await self.repo.alias_exists(payload.custom_alias):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Custom alias already taken"
            )

        url = await self.repo.create(
            owner_id=owner_id,
            target_url=payload.target_url,
            custom_alias=payload.custom_alias,
            expires_at=payload.expires_at,
            title=payload.title,
        )

        # Populate cache immediately (write-through on create) so the very
        # first redirect is a cache hit, not a guaranteed miss.
        await self.cache.set_url(
            url.effective_code,
            url_id=url.id,
            target_url=url.target_url,
            owner_id=str(url.owner_id),
            is_active=url.is_active,
            expires_at=url.expires_at,
        )
        from app.core.metrics import urls_created_total
        urls_created_total.inc()
        return self._to_read(url)

    async def get_owned(self, owner_id: uuid.UUID, url_id: int) -> URL:
        url = await self.repo.get_by_id(url_id)
        if url is None or url.owner_id != owner_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="URL not found")
        return url

    async def list_for_owner(
        self,
        owner_id: uuid.UUID,
        *,
        page: int,
        page_size: int,
        search: str | None,
        is_active: bool | None,
    ) -> URLListResponse:
        items, total = await self.repo.list_for_owner(
            owner_id, page=page, page_size=page_size, search=search, is_active=is_active
        )
        return URLListResponse(
            items=[self._to_read(u) for u in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=max(1, math.ceil(total / page_size)),
        )

    async def update(self, owner_id: uuid.UUID, url_id: int, payload: URLUpdate) -> URLRead:
        url = await self.get_owned(owner_id, url_id)
        old_code = url.effective_code

        url = await self.repo.update(
            url,
            target_url=payload.target_url,
            expires_at=payload.expires_at,
            is_active=payload.is_active,
            title=payload.title,
        )

        # Invalidate old + (possibly changed) new cache entry rather than
        # trying to patch the cached blob in place — simpler and avoids
        # subtle staleness bugs.
        await self.cache.invalidate(old_code, url.effective_code)
        if url.is_active:
            await self.cache.set_url(
                url.effective_code,
                url_id=url.id,
                target_url=url.target_url,
                owner_id=str(url.owner_id),
                is_active=url.is_active,
                expires_at=url.expires_at,
            )
        return self._to_read(url)

    async def delete(self, owner_id: uuid.UUID, url_id: int) -> None:
        url = await self.get_owned(owner_id, url_id)
        await self.cache.invalidate(url.effective_code)
        await self.repo.delete(url)

    def _to_read(self, url: URL) -> URLRead:
        return URLRead(
            id=url.id,
            short_code=url.short_code,
            custom_alias=url.custom_alias,
            target_url=url.target_url,
            title=url.title,
            created_at=url.created_at,
            expires_at=url.expires_at,
            is_active=url.is_active,
            total_clicks=url.total_clicks,
            short_url=f"{settings.SHORT_URL_BASE}/{url.effective_code}",
        )
