import asyncpg
from app.config import get_settings

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        raise RuntimeError("Database pool not initialised")
    return _pool


async def init_pool() -> None:
    global _pool
    s = get_settings()
    _pool = await asyncpg.create_pool(
        host=s.POSTGRES_HOST,
        port=s.POSTGRES_PORT,
        user=s.POSTGRES_USER,
        password=s.POSTGRES_PASSWORD,
        database=s.AUTH_DB_NAME,
        min_size=2,
        max_size=10,
    )


async def close_pool() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
