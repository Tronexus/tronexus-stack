import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt
from passlib.context import CryptContext

from app.config import get_settings
from app.db.postgres import get_pool

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(payload: dict[str, Any]) -> str:
    s = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=s.AUTH_ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {**payload, "exp": expire, "iat": datetime.now(timezone.utc)},
        s.AUTH_JWT_SECRET, algorithm=s.AUTH_JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    s = get_settings()
    return jwt.decode(token, s.AUTH_JWT_SECRET, algorithms=[s.AUTH_JWT_ALGORITHM])


async def create_refresh_token(user_id: uuid.UUID, family_id: uuid.UUID | None = None) -> str:
    s = get_settings()
    pool = await get_pool()
    if family_id is None:
        family_id = uuid.uuid4()
    secret = secrets.token_urlsafe(48)
    hashed = pwd_context.hash(secret)
    expires_at = datetime.now(timezone.utc) + timedelta(days=s.AUTH_REFRESH_TOKEN_EXPIRE_DAYS)
    row = await pool.fetchrow(
        "INSERT INTO refresh_tokens (user_id, token_hash, family_id, expires_at) VALUES ($1, $2, $3, $4) RETURNING id",
        user_id, hashed, family_id, expires_at,
    )
    return f"{row['id']}.{secret}"


async def rotate_refresh_token(plain_token: str) -> tuple[str, uuid.UUID]:
    pool = await get_pool()
    try:
        token_id_str, secret = plain_token.split(".", 1)
        token_id = uuid.UUID(token_id_str)
    except (ValueError, AttributeError):
        raise ValueError("Invalid token format")
    row = await pool.fetchrow("SELECT * FROM refresh_tokens WHERE id = $1", token_id)
    if row is None:
        raise ValueError("Token not found")
    if row["revoked"] or row["used_at"] is not None:
        await pool.execute("UPDATE refresh_tokens SET revoked = true WHERE family_id = $1", row["family_id"])
        raise ValueError("Token replay detected — session revoked")
    if row["expires_at"].replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise ValueError("Token expired")
    if not pwd_context.verify(secret, row["token_hash"]):
        raise ValueError("Invalid token")
    await pool.execute("UPDATE refresh_tokens SET used_at = now() WHERE id = $1", token_id)
    new_plain = await create_refresh_token(row["user_id"], family_id=row["family_id"])
    return new_plain, row["user_id"]


async def revoke_user_tokens(user_id: uuid.UUID) -> None:
    pool = await get_pool()
    await pool.execute(
        "UPDATE refresh_tokens SET revoked = true WHERE user_id = $1 AND revoked = false", user_id,
    )
