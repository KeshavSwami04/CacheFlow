"""
Single shared async Redis connection pool for the API process.
redis-py's async client is itself a thin wrapper over a connection pool,
so one global client is the correct pattern (not one connection per
request).
"""
import redis.asyncio as redis

from app.core.config import settings

redis_client: redis.Redis = redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    max_connections=50,
)


async def get_redis() -> redis.Redis:
    return redis_client
