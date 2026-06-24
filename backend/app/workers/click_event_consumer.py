"""
Click event consumer.

Consumes from `click_events.process`, persists the click (raw event +
daily rollup upsert + denormalized total_clicks bump on `urls`), bumps the
live `metrics:events:processed` counter Redis reads for the Architecture
Dashboard, and heartbeats into Redis so the dashboard can show worker
liveness.

Retry strategy: on a processing failure we don't just `nack(requeue=True)`
(that would redeliver instantly and could tight-loop against a transient
DB outage). Instead we track `retry_count` in the message body, and on
failure either:
  - republish to the same queue with `retry_count + 1` after an
    exponential backoff sleep (bounded, in-process — fine at this scale;
    a delayed-exchange plugin would replace this for true distributed
    backoff), or
  - once `retry_count` exceeds the configured max, `nack(requeue=False)`,
    which — because the queue was declared with
    `x-dead-letter-exchange=click_events.dlx` — causes RabbitMQ itself to
    route the message to `click_events.dlq` (see app/core/rabbitmq.py).
"""
import asyncio
import json
import time

import aio_pika
import structlog
from aio_pika.abc import AbstractIncomingMessage

from app.core.config import settings
from app.db.redis_client import redis_client
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.url_repository import URLRepository
from app.services.system_metrics_service import PROCESSED_EVENTS_KEY
from app.utils.mock_geo import mock_country_for_ip_hash
from app.workers.db import new_worker_session

logger = structlog.get_logger("click_event_consumer")

_DEVICE_KEYWORDS = (("mobile", "mobile"), ("tablet", "tablet"), ("bot", "bot"))


def _classify_device(user_agent: str | None) -> str:
    if not user_agent:
        return "unknown"
    ua_lower = user_agent.lower()
    for keyword, label in _DEVICE_KEYWORDS:
        if keyword in ua_lower:
            return label
    return "desktop"


async def _persist_click(payload: dict) -> None:
    async with new_worker_session() as session:
        analytics_repo = AnalyticsRepository(session)
        url_repo = URLRepository(session)

        country = mock_country_for_ip_hash(payload.get("ip_hash"))
        device = _classify_device(payload.get("user_agent"))

        await analytics_repo.record_click(
            url_id=payload["url_id"],
            referrer=payload.get("referrer"),
            country_code=country,
            device_type=device,
            ip_hash=payload.get("ip_hash"),
        )
        await url_repo.increment_total_clicks(payload["url_id"])


async def _republish_with_backoff(
    message: AbstractIncomingMessage, payload: dict, exchange: aio_pika.Exchange
) -> None:
    retry_count = payload.get("retry_count", 0) + 1
    payload["retry_count"] = retry_count
    backoff_seconds = min(2 ** retry_count, 30)

    logger.warning(
        "click_event_retry_scheduled",
        retry_count=retry_count,
        backoff_seconds=backoff_seconds,
        url_id=payload.get("url_id"),
    )
    await asyncio.sleep(backoff_seconds)

    await exchange.publish(
        aio_pika.Message(
            body=json.dumps(payload).encode(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            content_type="application/json",
        ),
        routing_key="click.created",
    )


async def handle_message(
    message: AbstractIncomingMessage, exchange: aio_pika.Exchange
) -> None:
    try:
        payload = json.loads(message.body)
    except json.JSONDecodeError:
        logger.error("click_event_malformed_payload_dropping")
        await message.ack()  # unparseable junk should not retry forever
        return

    try:
        await _persist_click(payload)
        await redis_client.incr(PROCESSED_EVENTS_KEY)
        await message.ack()
        logger.info("click_event_processed", url_id=payload.get("url_id"))
    except Exception:
        logger.exception("click_event_processing_failed", url_id=payload.get("url_id"))
        retry_count = payload.get("retry_count", 0)
        if retry_count < settings.CLICK_EVENT_MAX_RETRIES:
            await _republish_with_backoff(message, payload, exchange)
            await message.ack()  # original superseded by the republished retry copy
        else:
            logger.error(
                "click_event_max_retries_exceeded_dead_lettering",
                url_id=payload.get("url_id"),
            )
            await message.nack(requeue=False)  # routed to DLQ by the queue's DLX config


async def heartbeat_loop(worker_id: str) -> None:
    while True:
        await redis_client.set(
            f"worker:heartbeat:{worker_id}",
            time.time(),
            ex=settings.WORKER_HEARTBEAT_TTL_SECONDS * 2
        )
        await asyncio.sleep(settings.WORKER_HEARTBEAT_INTERVAL_SECONDS)
