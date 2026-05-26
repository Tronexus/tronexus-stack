import time
from app.db.redis import get_redis
from app.db.postgres import get_pool
from app.config import get_settings


async def is_banned(ip: str) -> bool:
    redis = get_redis()
    if await redis.exists(f"lockout:{ip}"):
        return True
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT 1 FROM rate_limit_bans WHERE ip = $1 AND (expires_at IS NULL OR expires_at > now())", ip,
    )
    return row is not None


async def check_rate_limit(ip: str, endpoint: str) -> bool:
    s = get_settings()
    redis = get_redis()
    now = time.time()
    window_start = now - s.AUTH_RATE_LIMIT_WINDOW
    key = f"rl:{endpoint}:{ip}"
    pipe = redis.pipeline()
    pipe.zremrangebyscore(key, "-inf", window_start)
    pipe.zadd(key, {f"{now}": now})
    pipe.zcard(key)
    pipe.expire(key, s.AUTH_RATE_LIMIT_WINDOW)
    results = await pipe.execute()
    if results[2] > s.AUTH_RATE_LIMIT_MAX:
        await _trigger_lockout(ip)
        return False
    return True


async def _trigger_lockout(ip: str) -> None:
    s = get_settings()
    redis = get_redis()
    await redis.set(f"lockout:{ip}", "1", ex=s.AUTH_LOCKOUT_SECONDS, nx=True)
