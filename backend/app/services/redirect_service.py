import hashlib
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.repositories.url_repository import URLRepository
from app.services.cache_service import CacheService
from app.services.event_publisher import event_publisher


def hash_ip(ip: str) -> str:
    """One-way hash so we never persist a raw client IP (see ClickEvent model)."""
    return hashlib.sha256(f"{ip}{settings.SECRET_KEY}".encode()).hexdigest()[:32]


class RedirectService:
    def __init__(self, db: AsyncSession, cache: CacheService):
        self.repo = URLRepository(db)
        self.cache = cache

    async def resolve(
        self, code: str, *, referrer: str | None, user_agent: str | None, client_ip: str
    ) -> str:
        """
        Cache-aside resolution per ARCHITECTURE.md section 4:
        1. Try Redis.
        2. On miss, read-through Postgres and populate Redis.
        3. Validate active/expiry.
        4. Fire-and-forget publish a click event (never blocks the redirect).
        """
        cached = await self.cache.get_url(code)

        if cached is not None:
            if not cached["is_active"]:
                raise HTTPException(status_code=status.HTTP_410_GONE, detail="This link has been deactivated")
            if cached["expires_at"] and datetime.fromisoformat(cached["expires_at"]) <= datetime.now(timezone.utc):
                raise HTTPException(status_code=status.HTTP_410_GONE, detail="This link has expired")
            target_url = cached["target_url"]
            url_id = cached["url_id"]
        else:
            url = await self.repo.get_by_code(code)
            if url is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Short URL not found")
            if not url.is_active:
                raise HTTPException(status_code=status.HTTP_410_GONE, detail="This link has been deactivated")
            if await self.repo.is_expired(url):
                raise HTTPException(status_code=status.HTTP_410_GONE, detail="This link has expired")

            await self.cache.set_url(
                url.effective_code,
                url_id=url.id,
                target_url=url.target_url,
                owner_id=str(url.owner_id),
                is_active=url.is_active,
                expires_at=url.expires_at,
            )
            target_url, url_id = url.target_url, url.id

        await event_publisher.publish_click_event(
            url_id=url_id,
            short_code=code,
            referrer=referrer,
            user_agent=user_agent,
            ip_hash=hash_ip(client_ip),
        )
        from app.core.metrics import redirects_total
        redirects_total.inc()
        return target_url
