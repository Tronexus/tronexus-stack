import asyncpg
from app.config import get_settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS apps (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT UNIQUE NOT NULL,
    description TEXT,
    client_id   TEXT NOT NULL DEFAULT gen_random_uuid()::TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    app_id        UUID NOT NULL REFERENCES apps(id) ON DELETE CASCADE,
    google_id     TEXT NOT NULL,
    email         TEXT NOT NULL,
    name          TEXT,
    avatar_url    TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_login_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (app_id, google_id)
);

CREATE TABLE IF NOT EXISTS roles (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    app_id      UUID NOT NULL REFERENCES apps(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    description TEXT,
    UNIQUE (app_id, name)
);

CREATE TABLE IF NOT EXISTS user_roles (
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id     UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, role_id)
);

CREATE TABLE IF NOT EXISTS refresh_tokens (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash  TEXT NOT NULL,
    family_id   UUID NOT NULL,
    expires_at  TIMESTAMPTZ NOT NULL,
    used_at     TIMESTAMPTZ,
    revoked     BOOLEAN NOT NULL DEFAULT false,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS api_keys (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    app_id       UUID NOT NULL REFERENCES apps(id) ON DELETE CASCADE,
    name         TEXT NOT NULL,
    key_hash     TEXT NOT NULL,
    scopes       TEXT[] NOT NULL DEFAULT '{}',
    expires_at   TIMESTAMPTZ NOT NULL,
    last_used_at TIMESTAMPTZ,
    revoked      BOOLEAN NOT NULL DEFAULT false,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS rate_limit_bans (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ip         TEXT NOT NULL,
    reason     TEXT,
    banned_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_users_app_google      ON users(app_id, google_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user   ON refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_family ON refresh_tokens(family_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_app          ON api_keys(app_id);
CREATE INDEX IF NOT EXISTS idx_rate_limit_bans_ip    ON rate_limit_bans(ip);
"""


async def run_migrations() -> None:
    s = get_settings()

    sys_conn = await asyncpg.connect(
        host=s.POSTGRES_HOST,
        port=s.POSTGRES_PORT,
        user=s.POSTGRES_USER,
        password=s.POSTGRES_PASSWORD,
        database="postgres",
    )
    try:
        exists = await sys_conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", s.AUTH_DB_NAME
        )
        if not exists:
            await sys_conn.execute(f'CREATE DATABASE "{s.AUTH_DB_NAME}"')
    finally:
        await sys_conn.close()

    auth_conn = await asyncpg.connect(
        host=s.POSTGRES_HOST,
        port=s.POSTGRES_PORT,
        user=s.POSTGRES_USER,
        password=s.POSTGRES_PASSWORD,
        database=s.AUTH_DB_NAME,
    )
    try:
        await auth_conn.execute(SCHEMA)
    finally:
        await auth_conn.close()
