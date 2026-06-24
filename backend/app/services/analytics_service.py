import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.url_repository import URLRepository
from app.schemas.analytics import (
    CountryStat,
    DailyClickPoint,
    ReferrerStat,
    TopURLEntry,
    URLAnalyticsResponse,
    UserAnalyticsSummary,
)
class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.analytics_repo = AnalyticsRepository(db)
        self.url_repo = URLRepository(db)

    async def url_analytics(self, owner_id: uuid.UUID, url_id: int, days: int = 30) -> URLAnalyticsResponse:
        url = await self.url_repo.get_by_id(url_id)
        if url is None or url.owner_id != owner_id:
            from fastapi import HTTPException, status
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="URL not found")

        daily = await self.analytics_repo.daily_clicks_for_url(url_id, days)
        referrers = await self.analytics_repo.referrer_breakdown(url_id, days)
        countries = await self.analytics_repo.country_breakdown(url_id, days)

        return URLAnalyticsResponse(
            short_code=url.effective_code,
            total_clicks=url.total_clicks,
            daily_clicks=[DailyClickPoint(stat_date=d.stat_date, click_count=d.click_count) for d in daily],
            top_referrers=sorted(
                [ReferrerStat(referrer=k, count=v) for k, v in referrers.items()],
                key=lambda r: r.count, reverse=True,
            )[:10],
            top_countries=sorted(
                [CountryStat(country_code=k, count=v) for k, v in countries.items()],
                key=lambda c: c.count, reverse=True,
            )[:10],
        )

    async def user_summary(self, owner_id: uuid.UUID) -> UserAnalyticsSummary:
        top_urls = await self.url_repo.top_urls_for_owner(owner_id, limit=5)
        _, total_urls = await self.url_repo.list_for_owner(owner_id, page=1, page_size=1)
        clicks_today = await self.analytics_repo.clicks_today_for_owner(owner_id)
        daily = await self.analytics_repo.daily_clicks_for_owner(owner_id, days=14)
        total_clicks = sum(u.total_clicks for u in top_urls) if top_urls else 0

        # total_clicks across ALL urls (not just top 5) — cheap aggregate
        all_items, _ = await self.url_repo.list_for_owner(owner_id, page=1, page_size=1000)
        total_clicks = sum(u.total_clicks for u in all_items)

        return UserAnalyticsSummary(
            total_urls=total_urls,
            total_clicks=total_clicks,
            clicks_today=clicks_today,
            top_urls=[
                TopURLEntry(
                    short_code=u.effective_code,
                    target_url=u.target_url,
                    title=u.title,
                    total_clicks=u.total_clicks,
                )
                for u in top_urls
            ],
            daily_clicks=[DailyClickPoint(**d) for d in daily],
        )
