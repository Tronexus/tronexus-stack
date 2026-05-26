from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.db.migrations import run_migrations
from app.db.postgres import close_pool, init_pool
from app.db.redis import close_redis, init_redis
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.models.schemas import HealthResponse
from app.routers import apikeys, apps, auth, oauth


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_redis()
    await run_migrations()
    await init_pool()
    yield
    await close_pool()
    await close_redis()


app = FastAPI(
    title="Tronexus Auth",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)

app.include_router(oauth.router)
app.include_router(auth.router)
app.include_router(apps.router)
app.include_router(apikeys.router)


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse()
