import uuid
from datetime import datetime, timezone

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.url import URL
from app.utils.base62 import base62_encode
from app.utils.obfuscation import permute_id

# Added to the raw sequence id before encoding purely so short codes look
# like real-world short URLs from day one (e.g. "2bI9" instead of "1",
# "2", "3", ...) rather than leaking the exact row count. Decoding back
# to a DB id is never needed (lookups go by short_code string), so this
# offset has no functional effect beyond code aesthetics/length.
SHORT_CODE_ID_OFFSET = 1_000_000


class URLRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        *,
        owner_id: uuid.UUID,
        target_url: str,
        custom_alias: str | None,
        expires_at: datetime | None,
        title: str | None,
    ) -> URL:
        """
        Two-statement, single-transaction sequence: INSERT to obtain the
        PK from the urls_id_seq, then UPDATE to stamp short_code =
        base62(id). See ARCHITECTURE.md section 9.1 — this guarantees
        collision-free codes with no retry loop, at the cost of one extra
        UPDATE per create (acceptable: writes are rare relative to reads).
        """
        url = URL(
            owner_id=owner_id,
            target_url=target_url,
            custom_alias=custom_alias,
            expires_at=expires_at,
            title=title,
        )
        self.db.add(url)
        await self.db.flush()  # assigns url.id from the sequence, no commit yet

        url.short_code = base62_encode(permute_id(url.id + SHORT_CODE_ID_OFFSET))
        await self.db.commit()
        await self.db.refresh(url)
        return url

    async def get_by_code(self, code: str) -> URL | None:
        """Looks up by short_code OR custom_alias — either resolves a URL."""
        result = await self.db.execute(
            select(URL).where(or_(URL.short_code == code, URL.custom_alias == code))
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, url_id: int) -> URL | None:
        return await self.db.get(URL, url_id)

    async def alias_exists(self, alias: str) -> bool:
        result = await self.db.execute(select(URL.id).where(URL.custom_alias == alias))
        return result.scalar_one_or_none() is not None

    async def list_for_owner(
        self,
        owner_id: uuid.UUID,
        *,
        page: int,
        page_size: int,
        search: str | None = None,
        is_active: bool | None = None,
    ) -> tuple[list[URL], int]:
        filters = [URL.owner_id == owner_id]
        if search:
            like = f"%{search}%"
            filters.append(
                or_(URL.target_url.ilike(like), URL.short_code.ilike(like),
                    URL.custom_alias.ilike(like), URL.title.ilike(like))
            )
        if is_active is not None:
            filters.append(URL.is_active == is_active)

        count_result = await self.db.execute(
            select(func.count()).select_from(URL).where(*filters)
        )
        total = count_result.scalar_one()

        result = await self.db.execute(
            select(URL)
            .where(*filters)
            .order_by(URL.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), total

    async def update(self, url: URL, **fields) -> URL:
        for key, value in fields.items():
            if value is not None:
                setattr(url, key, value)
        await self.db.commit()
        await self.db.refresh(url)
        return url

    async def delete(self, url: URL) -> None:
        await self.db.delete(url)
        await self.db.commit()

    async def increment_total_clicks(self, url_id: int, by: int = 1) -> None:
        await self.db.execute(
            update(URL).where(URL.id == url_id).values(total_clicks=URL.total_clicks + by)
        )
        await self.db.commit()

    async def top_urls_for_owner(self, owner_id: uuid.UUID, limit: int = 5) -> list[URL]:
        result = await self.db.execute(
            select(URL)
            .where(URL.owner_id == owner_id)
            .order_by(URL.total_clicks.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def is_expired(self, url: URL) -> bool:
        return bool(url.expires_at and url.expires_at <= datetime.now(timezone.utc))
