"""
Redis cache-aside layer for short_code -> URL resolution (the hot path).

Pattern: lazy loading on read, explicit invalidation on write. See
ARCHITECTURE.md section 6 for the full key map. This module is the single
place that knows the Redis key schema for URL caching + cache metrics, so
nothing else constructs these keys by hand.
"""
import json
from datetime import datetime

import redis.asyncio as redis

CACHE_KEY_PREFIX = "url:"
METRIC_HITS_KEY = "metrics:cache:hits"
METRIC_MISSES_KEY = "metrics:cache:misses"


class CacheService:
    def __init__(self, redis_client: redis.Redis, ttl_seconds: int = 3600):
        self.redis = redis_client
        self.ttl_seconds = ttl_seconds

    @staticmethod
    def _key(code: str) -> str:
        return f"{CACHE_KEY_PREFIX}{code}"

    async def get_url(self, code: str) -> dict | None:
        raw = await self.redis.get(self._key(code))
        if raw is None:
            await self.redis.incr(METRIC_MISSES_KEY)
            from app.core.metrics import cache_misses_total
            cache_misses_total.inc()
            return None
        await self.redis.incr(METRIC_HITS_KEY)
        from app.core.metrics import cache_hits_total
        cache_hits_total.inc()
        return json.loads(raw)

    async def set_url(
        self,
        code: str,
        *,
        url_id: int,
        target_url: str,
        owner_id: str,
        is_active: bool,
        expires_at: datetime | None,
    ) -> None:
        payload = {
            "url_id": url_id,
            "target_url": target_url,
            "owner_id": owner_id,
            "is_active": is_active,
            "expires_at": expires_at.isoformat() if expires_at else None,
        }
        await self.redis.set(self._key(code), json.dumps(payload), ex=self.ttl_seconds)

    async def invalidate(self, *codes: str) -> None:
        keys = [self._key(code) for code in codes if code]
        if keys:
            await self.redis.delete(*keys)

    async def get_metrics(self) -> dict:
        hits_raw, misses_raw = await self.redis.mget(METRIC_HITS_KEY, METRIC_MISSES_KEY)
        hits = int(hits_raw or 0)
        misses = int(misses_raw or 0)
        total = hits + misses
        hit_rate = round(hits / total, 4) if total else 0.0
        return {"hits": hits, "misses": misses, "hit_rate": hit_rate}
