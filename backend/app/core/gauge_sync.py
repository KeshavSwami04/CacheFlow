"""
Bridges worker-side Redis metrics and RabbitMQ queue depths into the
Prometheus gauge registry every 15 seconds so a single /metrics scrape
from the API reflects the whole pipeline — no Pushgateway needed.
"""
import asyncio
import time

import aiohttp
import structlog

from app.core.config import settings
from app.core import metrics as m
from app.db.redis_client import redis_client
from app.db.session import engine
from app.services.system_metrics_service import PROCESSED_EVENTS_KEY, WORKER_HEARTBEAT_PREFIX

logger = structlog.get_logger("gauge_sync")

SYNC_INTERVAL_SECONDS = 15


async def _sync_once() -> None:
    try:
        # Worker heartbeats → active_workers gauge
        alive = 0
        now = time.time()
        async for key in redis_client.scan_iter(match=f"{WORKER_HEARTBEAT_PREFIX}*"):
            ts_raw = await redis_client.get(key)
            if ts_raw and (now - float(ts_raw)) <= settings.WORKER_HEARTBEAT_TTL_SECONDS:
                alive += 1
        m.active_workers_gauge.set(alive)

        # Events processed → gauge
        processed_raw = await redis_client.get(PROCESSED_EVENTS_KEY)
        m.events_processed_gauge.set(int(processed_raw or 0))

        # DB pool stats
        pool = engine.pool
        m.db_pool_checked_out_gauge.set(pool.checkedout())
        m.db_pool_size_gauge.set(pool.size())

        # RabbitMQ queue depths
        base = (
            f"http://{settings.RABBITMQ_HOST}:{settings.RABBITMQ_MANAGEMENT_PORT}/api/queues/%2F"
        )
        auth = aiohttp.BasicAuth(settings.RABBITMQ_USER, settings.RABBITMQ_PASSWORD)
        async with aiohttp.ClientSession(
            auth=auth, timeout=aiohttp.ClientTimeout(total=3)
        ) as session:
            for queue_name, gauge in [
                (settings.CLICK_EVENTS_QUEUE, m.queue_depth_gauge),
                (settings.CLICK_EVENTS_DLQ, m.dlq_depth_gauge),
            ]:
                try:
                    async with session.get(f"{base}/{queue_name}") as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            gauge.set(data.get("messages", 0))
                except Exception:
                    pass  # RabbitMQ briefly unavailable; keep the last value

    except Exception:
        logger.exception("gauge_sync_error")


async def gauge_sync_loop() -> None:
    """Run forever; meant to be launched as an asyncio.create_task in lifespan."""
    while True:
        await _sync_once()
        await asyncio.sleep(SYNC_INTERVAL_SECONDS)
