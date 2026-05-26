import secrets
import uuid
from datetime import datetime, timedelta, timezone

from passlib.context import CryptContext

from app.db.postgres import get_pool
from app.models.schemas import ApiKeyCreate

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def create_api_key(data: ApiKeyCreate) -> dict:
    pool = await get_pool()
    plain = f"ak_{secrets.token_urlsafe(32)}"
    hashed = pwd_context.hash(plain)
    expires_at = datetime.now(timezone.utc) + timedelta(days=data.expires_in_days)
    row = await pool.fetchrow(
        "INSERT INTO api_keys (app_id, name, key_hash, scopes, expires_at) VALUES ($1, $2, $3, $4, $5) RETURNING *",
        data.app_id, data.name, hashed, data.scopes, expires_at,
    )
    result = dict(row)
    result["key"] = plain
    return result


async def revoke_api_key(key_id: uuid.UUID) -> bool:
    pool = await get_pool()
    status = await pool.execute(
        "UPDATE api_keys SET revoked = true WHERE id = $1 AND revoked = false", key_id,
    )
    return status == "UPDATE 1"


async def verify_api_key(plain_key: str) -> dict | None:
    pool = await get_pool()
    rows = await pool.fetch("SELECT * FROM api_keys WHERE revoked = false AND expires_at > now()")
    for row in rows:
        if pwd_context.verify(plain_key, row["key_hash"]):
            await pool.execute("UPDATE api_keys SET last_used_at = now() WHERE id = $1", row["id"])
            return dict(row)
    return None
