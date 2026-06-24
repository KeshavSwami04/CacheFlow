"""
Publishes click events to RabbitMQ. Owns a single long-lived robust
connection + channel for the API process (opened at startup, reused
across requests) — opening a new AMQP connection per request would be
far too slow for something sitting in the redirect hot path.

Publish failures are caught and logged, never raised: per
ARCHITECTURE.md section 4, analytics is best-effort and must never break
a redirect.
"""
import json
from datetime import datetime, timezone

import aio_pika
import structlog
from aio_pika.abc import AbstractChannel, AbstractRobustConnection

from app.core.config import settings
from app.core.rabbitmq import declare_topology, get_connection

logger = structlog.get_logger("event_publisher")


class EventPublisher:
    def __init__(self) -> None:
        self._connection: AbstractRobustConnection | None = None
        self._channel: AbstractChannel | None = None
        self._exchange = None

    async def start(self) -> None:
        self._connection = await get_connection()
        self._channel = await self._connection.channel()
        self._exchange, _, _, _ = await declare_topology(self._channel)
        logger.info("event_publisher_started")

    async def stop(self) -> None:
        if self._connection:
            await self._connection.close()
            logger.info("event_publisher_stopped")

    async def publish_click_event(
        self,
        *,
        url_id: int,
        short_code: str,
        referrer: str | None,
        user_agent: str | None,
        ip_hash: str | None,
    ) -> None:
        if self._exchange is None:
            logger.warning("event_publisher_not_started_skipping_publish")
            return

        payload = {
            "url_id": url_id,
            "short_code": short_code,
            "referrer": referrer,
            "user_agent": user_agent,
            "ip_hash": ip_hash,
            "clicked_at": datetime.now(timezone.utc).isoformat(),
            "retry_count": 0,
        }
        try:
            message = aio_pika.Message(
                body=json.dumps(payload).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                content_type="application/json",
            )
            await self._exchange.publish(message, routing_key="click.created")
        except Exception:
            # Best-effort: a dropped click event must never surface to the
            # visitor as a failed redirect.
            logger.exception("click_event_publish_failed", url_id=url_id, short_code=short_code)


event_publisher = EventPublisher()
