import base64
import hashlib
import secrets
import uuid

import httpx

from app.config import get_settings
from app.db.postgres import get_pool
from app.db.redis import get_redis

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


def _generate_pkce() -> tuple[str, str]:
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
    digest = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return code_verifier, code_challenge


async def initiate_oauth(app_id: str) -> str:
    s = get_settings()
    pool = await get_pool()
    redis = get_redis()
    try:
        app_uuid = uuid.UUID(app_id)
    except ValueError:
        raise ValueError("Invalid app_id")
    row = await pool.fetchrow("SELECT id FROM apps WHERE id = $1", app_uuid)
    if not row:
        raise ValueError("App not found")
    state = secrets.token_urlsafe(32)
    code_verifier, code_challenge = _generate_pkce()
    await redis.setex(f"oauth_state:{state}", 600, f"{app_id}:{code_verifier}")
    params = {
        "client_id": s.AUTH_GOOGLE_CLIENT_ID,
        "redirect_uri": f"{s.AUTH_API_BASE_URL}/oauth/google/callback",
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "access_type": "offline",
        "prompt": "consent",
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{GOOGLE_AUTH_URL}?{query}"


async def handle_callback(code: str, state: str) -> tuple[uuid.UUID, str]:
    s = get_settings()
    redis = get_redis()
    stored = await redis.get(f"oauth_state:{state}")
    if not stored:
        raise ValueError("Invalid or expired state")
    await redis.delete(f"oauth_state:{state}")
    app_id_str, code_verifier = stored.split(":", 1)
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": s.AUTH_GOOGLE_CLIENT_ID,
                "client_secret": s.AUTH_GOOGLE_CLIENT_SECRET,
                "redirect_uri": f"{s.AUTH_API_BASE_URL}/oauth/google/callback",
                "grant_type": "authorization_code",
                "code_verifier": code_verifier,
            },
        )
        token_resp.raise_for_status()
        userinfo_resp = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {token_resp.json()['access_token']}"},
        )
        userinfo_resp.raise_for_status()
        userinfo = userinfo_resp.json()
    user_id = await _upsert_user(app_id_str, userinfo)
    return user_id, app_id_str


async def _upsert_user(app_id: str, userinfo: dict) -> uuid.UUID:
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO users (app_id, google_id, email, name, avatar_url)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (app_id, google_id) DO UPDATE SET
            email = EXCLUDED.email, name = EXCLUDED.name,
            avatar_url = EXCLUDED.avatar_url, last_login_at = now()
        RETURNING id
        """,
        uuid.UUID(app_id), userinfo["sub"], userinfo.get("email", ""),
        userinfo.get("name"), userinfo.get("picture"),
    )
    return row["id"]
