from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Google OAuth
    AUTH_GOOGLE_CLIENT_ID: str
    AUTH_GOOGLE_CLIENT_SECRET: str

    # JWT
    AUTH_JWT_SECRET: str
    AUTH_JWT_ALGORITHM: str = "HS256"
    AUTH_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    AUTH_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    AUTH_API_BASE_URL: str

    # Postgres
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str = "tronexus-postgres"
    POSTGRES_PORT: int = 5432
    AUTH_DB_NAME: str = "auth"

    # Redis
    REDIS_HOST: str = "tronexus-redis"
    REDIS_PORT: int = 6379

    # Rate limiting
    AUTH_RATE_LIMIT_WINDOW: int = 60
    AUTH_RATE_LIMIT_MAX: int = 20
    AUTH_LOCKOUT_ATTEMPTS: int = 10
    AUTH_LOCKOUT_SECONDS: int = 900

    model_config = {"env_file": ".env", "extra": "ignore", "case_sensitive": False}


@lru_cache
def get_settings() -> Settings:
    return Settings()
