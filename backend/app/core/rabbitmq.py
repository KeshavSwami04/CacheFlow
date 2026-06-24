"""
RabbitMQ topology declaration + a shared robust connection helper.

Topology (see ARCHITECTURE.md section 7):
  exchange "click_events" (topic, durable)
    -> queue "click_events.process" (durable, DLX -> click_events.dlx)
  exchange "click_events.dlx" (fanout, durable)
    -> queue "click_events.dlq" (durable)

Both the API (publisher) and the worker (consumer) call `declare_topology`
on startup so either one can come up first without ordering assumptions —
idempotent declaration is the standard AMQP pattern for this.
"""
import aio_pika
from aio_pika import ExchangeType
from aio_pika.abc import AbstractRobustConnection

from app.core.config import settings


async def get_connection() -> AbstractRobustConnection:
    return await aio_pika.connect_robust(settings.RABBITMQ_URL)


async def declare_topology(channel: aio_pika.abc.AbstractChannel) -> tuple:
    dlx = await channel.declare_exchange(
        settings.CLICK_EVENTS_DLX, ExchangeType.FANOUT, durable=True
    )
    dlq = await channel.declare_queue(settings.CLICK_EVENTS_DLQ, durable=True)
    await dlq.bind(dlx)

    main_exchange = await channel.declare_exchange(
        settings.CLICK_EVENTS_EXCHANGE, ExchangeType.TOPIC, durable=True
    )
    main_queue = await channel.declare_queue(
        settings.CLICK_EVENTS_QUEUE,
        durable=True,
        arguments={"x-dead-letter-exchange": settings.CLICK_EVENTS_DLX},
    )
    await main_queue.bind(main_exchange, routing_key="click.created")

    return main_exchange, main_queue, dlx, dlq
