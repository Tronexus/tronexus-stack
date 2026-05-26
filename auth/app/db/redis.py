import redis.asyncio as aioredis
from app.config import get_settings

_client: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    if _client is None:
        raise RuntimeError("Redis client not initialised")
    return _client


async def init_redis() -> None:
    global _client
    s = get_settings()
    _client = aioredis.Redis(host=s.REDIS_HOST, port=s.REDIS_PORT, decode_responses=True)
    await _client.ping()


async def close_redis() -> None:
    global _client
    if _client:
        await _client.aclose()
        _client = None
