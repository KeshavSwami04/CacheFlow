import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import cast, func, select
from sqlalchemy.dialects.postgresql import ARRAY, TEXT, insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.click_event import ClickEvent, URLDailyStat
from app.models.url import URL


class AnalyticsRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # --- Write path (called by the worker, never the redirect endpoint) ---

    async def record_click(
        self,
        *,
        url_id: int,
        referrer: str | None,
        country_code: str | None,
        device_type: str | None,
        ip_hash: str | None,
        clicked_at: datetime | None = None,
    ) -> None:
        clicked_at = clicked_at or datetime.now(timezone.utc)
        event = ClickEvent(
            url_id=url_id,
            referrer=referrer,
            country_code=country_code,
            device_type=device_type,
            ip_hash=ip_hash,
            clicked_at=clicked_at,
        )
        self.db.add(event)
        await self._upsert_daily_stat(url_id, clicked_at.date(), referrer, country_code)
        await self.db.commit()

    async def _upsert_daily_stat(
        self, url_id: int, stat_date: date, referrer: str | None, country_code: str | None
    ) -> None:
        referrer_key = referrer or "direct"
        country_key = country_code or "XX"

        stmt = (
            pg_insert(URLDailyStat)
            .values(
                url_id=url_id,
                stat_date=stat_date,
                click_count=1,
                referrer_breakdown={referrer_key: 1},
                country_breakdown={country_key: 1},
            )
            .on_conflict_do_update(
                index_elements=[URLDailyStat.url_id, URLDailyStat.stat_date],
                set_={
                    "click_count": URLDailyStat.click_count + 1,
                    "referrer_breakdown": func.jsonb_set(
                        URLDailyStat.referrer_breakdown,
                        cast([referrer_key], ARRAY(TEXT)),
                        func.to_jsonb(
                            func.coalesce(
                                URLDailyStat.referrer_breakdown[referrer_key].as_integer(), 0
                            )
                            + 1
                        ),
                        True,
                    ),
                    "country_breakdown": func.jsonb_set(
                        URLDailyStat.country_breakdown,
                        cast([country_key], ARRAY(TEXT)),
                        func.to_jsonb(
                            func.coalesce(
                                URLDailyStat.country_breakdown[country_key].as_integer(), 0
                            )
                            + 1
                        ),
                        True,
                    ),
                },
            )
        )
        await self.db.execute(stmt)

    # --- Read path (used by the analytics API) ---

    async def daily_clicks_for_url(self, url_id: int, days: int = 30) -> list[URLDailyStat]:
        since = date.today() - timedelta(days=days)
        result = await self.db.execute(
            select(URLDailyStat)
            .where(URLDailyStat.url_id == url_id, URLDailyStat.stat_date >= since)
            .order_by(URLDailyStat.stat_date.asc())
        )
        return list(result.scalars().all())

    async def daily_clicks_for_owner(self, owner_id: uuid.UUID, days: int = 14) -> list[dict]:
        since = date.today() - timedelta(days=days)
        result = await self.db.execute(
            select(URLDailyStat.stat_date, func.sum(URLDailyStat.click_count))
            .join(URL, URL.id == URLDailyStat.url_id)
            .where(URL.owner_id == owner_id, URLDailyStat.stat_date >= since)
            .group_by(URLDailyStat.stat_date)
            .order_by(URLDailyStat.stat_date.asc())
        )
        return [{"stat_date": row[0], "click_count": int(row[1])} for row in result.all()]

    async def clicks_today_for_owner(self, owner_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.coalesce(func.sum(URLDailyStat.click_count), 0))
            .join(URL, URL.id == URLDailyStat.url_id)
            .where(URL.owner_id == owner_id, URLDailyStat.stat_date == date.today())
        )
        return int(result.scalar_one())

    async def referrer_breakdown(self, url_id: int, days: int = 30) -> dict[str, int]:
        stats = await self.daily_clicks_for_url(url_id, days)
        merged: dict[str, int] = {}
        for stat in stats:
            for ref, count in (stat.referrer_breakdown or {}).items():
                merged[ref] = merged.get(ref, 0) + int(count)
        return merged

    async def country_breakdown(self, url_id: int, days: int = 30) -> dict[str, int]:
        stats = await self.daily_clicks_for_url(url_id, days)
        merged: dict[str, int] = {}
        for stat in stats:
            for country, count in (stat.country_breakdown or {}).items():
                merged[country] = merged.get(country, 0) + int(count)
        return merged
