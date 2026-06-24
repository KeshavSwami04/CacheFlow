"""
Sliding-window rate limiter backed by a Redis sorted set per key, scored
by request timestamp (ms). Implemented as a Lua script so the
read-trim-count-add sequence is atomic across concurrent requests hitting
the same key from different API replicas — without this, two replicas
could both read "9 of 10 used" and both admit a 10th+11th request.

Algorithm (per call):
  1. ZREMRANGEBYSCORE key 0 (now - window)   -- drop entries outside the window
  2. ZCARD key                               -- count what's left
  3. if count < limit: ZADD key now now; PEXPIRE key window  -- admit
  4. else: reject
"""
import time

import redis.asyncio as redis

_SLIDING_WINDOW_LUA = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window_ms = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])

redis.call('ZREMRANGEBYSCORE', key, 0, now - window_ms)
local count = redis.call('ZCARD', key)

if count < limit then
    redis.call('ZADD', key, now, now .. '-' .. math.random())
    redis.call('PEXPIRE', key, window_ms)
    return {1, limit - count - 1}
else
    return {0, 0}
end
"""


class RateLimiter:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self._script = self.redis.register_script(_SLIDING_WINDOW_LUA)

    async def allow(self, key: str, *, limit: int, window_seconds: int) -> tuple[bool, int]:
        """Returns (allowed, remaining)."""
        now_ms = int(time.time() * 1000)
        window_ms = window_seconds * 1000
        allowed, remaining = await self._script(keys=[key], args=[now_ms, window_ms, limit])
        return bool(allowed), int(remaining)
