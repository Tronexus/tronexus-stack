from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from app.services.token_service import decode_access_token
from app.services.apikey_service import verify_api_key

bearer = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(bearer)) -> dict:
    try:
        return decode_access_token(credentials.credentials)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")


async def require_admin_api_key(credentials: HTTPAuthorizationCredentials = Security(bearer)) -> dict:
    result = await verify_api_key(credentials.credentials)
    if result is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    if "admin" not in result["scopes"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient scope")
    return result
