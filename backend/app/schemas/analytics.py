from datetime import date

from pydantic import BaseModel


class DailyClickPoint(BaseModel):
    stat_date: date
    click_count: int


class TopURLEntry(BaseModel):
    short_code: str
    target_url: str
    title: str | None
    total_clicks: int


class ReferrerStat(BaseModel):
    referrer: str
    count: int


class CountryStat(BaseModel):
    country_code: str
    count: int


class URLAnalyticsResponse(BaseModel):
    short_code: str
    total_clicks: int
    daily_clicks: list[DailyClickPoint]
    top_referrers: list[ReferrerStat]
    top_countries: list[CountryStat]


class UserAnalyticsSummary(BaseModel):
    total_urls: int
    total_clicks: int
    clicks_today: int
    top_urls: list[TopURLEntry]
    daily_clicks: list[DailyClickPoint]


# --- Architecture / system metrics dashboard ---

class CacheMetrics(BaseModel):
    hits: int
    misses: int
    hit_rate: float


class QueueMetrics(BaseModel):
    queue_depth: int
    dlq_depth: int
    processed_events: int


class WorkerStatus(BaseModel):
    worker_id: str
    last_heartbeat_seconds_ago: float
    alive: bool


class SystemMetricsResponse(BaseModel):
    cache: CacheMetrics
    queue: QueueMetrics
    workers: list[WorkerStatus]
    db_pool_size: int
    db_pool_checked_out: int
