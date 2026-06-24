"""
Worker process entrypoint. Run as its own container (see
backend/Dockerfile.worker and docker-compose.yml's `worker` service) —
scale horizontally by increasing replica count; RabbitMQ's competing-
consumers pattern on a single queue means N workers just means N times
the throughput, no coordination needed between them.
"""
import asyncio
import os
import uuid

import structlog

from app.core.config import settings
from app.core.logging import configure_logging
from app.core.rabbitmq import declare_topology, get_connection
from app.workers.click_event_consumer import handle_message, heartbeat_loop

configure_logging()
logger = structlog.get_logger("worker_main")

WORKER_ID = os.environ.get("WORKER_ID", f"worker-{uuid.uuid4().hex[:8]}")


async def consume() -> None:
    connection = await get_connection()
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=settings.WORKER_PREFETCH_COUNT)

    exchange, queue, _, _ = await declare_topology(channel)

    logger.info("worker_consuming", worker_id=WORKER_ID, queue=settings.CLICK_EVENTS_QUEUE)

    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            await handle_message(message, exchange)


async def main() -> None:
    logger.info("worker_starting", worker_id=WORKER_ID)
    await asyncio.gather(
        consume(),
        heartbeat_loop(WORKER_ID),
    )


if __name__ == "__main__":
    asyncio.run(main())
