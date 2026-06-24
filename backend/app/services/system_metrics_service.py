"""
Aggregates live system metrics for the Architecture Dashboard:
cache hit/miss rate, RabbitMQ queue + DLQ depth (via the management HTTP
API), worker liveness (via Redis heartbeats), and DB pool utilization.
This endpoint is read-only and intentionally has no side effects.
"""
import time

import aiohttp
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import settings
from app.schemas.analytics import CacheMetrics, QueueMetrics, SystemMetricsResponse, WorkerStatus
from app.services.cache_service import CacheService

PROCESSED_EVENTS_KEY = "metrics:events:processed"
WORKER_HEARTBEAT_PREFIX = "worker:heartbeat:"


class SystemMetricsService:
    def __init__(self, redis_client: redis.Redis, cache_service: CacheService, engine: AsyncEngine):
        self.redis = redis_client
        self.cache_service = cache_service
        self.engine = engine

    async def get_metrics(self) -> SystemMetricsResponse:
        cache_raw = await self.cache_service.get_metrics()
        queue = await self._queue_metrics()
        workers = await self._worker_statuses()
        pool = self.engine.pool

        return SystemMetricsResponse(
            cache=CacheMetrics(**cache_raw),
            queue=queue,
            workers=workers,
            db_pool_size=pool.size(),
            db_pool_checked_out=pool.checkedout(),
        )

    async def _queue_metrics(self) -> QueueMetrics:
        processed_raw = await self.redis.get(PROCESSED_EVENTS_KEY)
        processed = int(processed_raw or 0)

        queue_depth, dlq_depth = 0, 0
        url = (
            f"http://{settings.RABBITMQ_HOST}:{settings.RABBITMQ_MANAGEMENT_PORT}"
            f"/api/queues/%2F"
        )
        auth = aiohttp.BasicAuth(settings.RABBITMQ_USER, settings.RABBITMQ_PASSWORD)
        try:
            async with aiohttp.ClientSession(auth=auth, timeout=aiohttp.ClientTimeout(total=2)) as session:
                async with session.get(f"{url}/{settings.CLICK_EVENTS_QUEUE}") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        queue_depth = data.get("messages", 0)
                async with session.get(f"{url}/{settings.CLICK_EVENTS_DLQ}") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        dlq_depth = data.get("messages", 0)
        except Exception:
            # Management API briefly unavailable shouldn't 500 the dashboard;
            # surface zeros rather than failing the whole metrics call.
            pass

        return QueueMetrics(queue_depth=queue_depth, dlq_depth=dlq_depth, processed_events=processed)

    async def _worker_statuses(self) -> list[WorkerStatus]:
        statuses: list[WorkerStatus] = []
        now = time.time()
        async for key in self.redis.scan_iter(match=f"{WORKER_HEARTBEAT_PREFIX}*"):
            ts_raw = await self.redis.get(key)
            if ts_raw is None:
                continue
            last_seen = float(ts_raw)
            age = now - last_seen
            worker_id = key.removeprefix(WORKER_HEARTBEAT_PREFIX)
            statuses.append(
                WorkerStatus(
                    worker_id=worker_id,
                    last_heartbeat_seconds_ago=round(age, 1),
                    alive=age <= settings.WORKER_HEARTBEAT_TTL_SECONDS,
                )
            )
        return sorted(statuses, key=lambda w: w.worker_id)
