#!/bin/bash
# =============================================================================
# TRONEXUS STACK — Auth Bootstrap
# =============================================================================
# Creates the default app and first admin API key in the auth database.
# Run once after initial installation.
# =============================================================================

set -a
source /opt/tronexus/.env
set +a

echo "Bootstrapping Tronexus auth..."

OUTPUT=$(docker run --rm \
  --network tronexus_tronexus \
  --env-file /opt/tronexus/.env \
  -e POSTGRES_HOST=tronexus-postgres \
  tronexus-stack-auth \
  python3 -c "
import asyncio, asyncpg, os, secrets
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone

pwd = CryptContext(schemes=['bcrypt'], deprecated='auto')

async def bootstrap():
    conn = await asyncpg.connect(
        host=os.environ['POSTGRES_HOST'],
        port=int(os.environ.get('POSTGRES_PORT', 5432)),
        user=os.environ['POSTGRES_USER'],
        password=os.environ['POSTGRES_PASSWORD'],
        database='auth',
    )
    app = await conn.fetchrow(
        \"\"\"INSERT INTO apps (name, description)
        VALUES ('tronexus', 'Primary Tronexus platform app')
        ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
        RETURNING id, name\"\"\"
    )
    print(f'APP_ID={app[\"id\"]}')

    plain = f'ak_{secrets.token_urlsafe(32)}'
    hashed = pwd.hash(plain)
    expires_at = datetime.now(timezone.utc) + timedelta(days=365)

    key = await conn.fetchrow(
        \"\"\"INSERT INTO api_keys (app_id, name, key_hash, scopes, expires_at)
        VALUES (\$1, 'admin-bootstrap', \$2, ARRAY['admin'], \$3)
        RETURNING id\"\"\",
        app['id'], hashed, expires_at
    )
    print(f'KEY_ID={key[\"id\"]}')
    print(f'API_KEY={plain}')
    await conn.close()

asyncio.run(bootstrap())
")

APP_ID=$(echo "$OUTPUT" | grep APP_ID | cut -d= -f2)
KEY_ID=$(echo "$OUTPUT" | grep KEY_ID | cut -d= -f2)
API_KEY=$(echo "$OUTPUT" | grep API_KEY | cut -d= -f2)

# Write APP_ID back to .env
if grep -q "^AUTH_APP_ID=" /opt/tronexus/.env; then
    sed -i "s/^AUTH_APP_ID=.*/AUTH_APP_ID=${APP_ID}/" /opt/tronexus/.env
else
    echo "AUTH_APP_ID=${APP_ID}" >> /opt/tronexus/.env
fi

echo ""
echo "============================================================"
echo "  Auth bootstrap complete"
echo "============================================================"
echo ""
echo "  App ID:  ${APP_ID}"
echo "  Key ID:  ${KEY_ID}"
echo "  API Key: ${API_KEY}"
echo ""
echo "  Store the API Key in your password manager."
echo "  It will NOT be shown again."
echo "  App ID has been written to .env as AUTH_APP_ID."
echo ""
echo "  OAuth entry point:"
echo "  https://auth-api.${TRONEXUS_DOMAIN}/oauth/google?app_id=${APP_ID}"
echo "============================================================"
