from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse

from app.config import get_settings
from app.services.oauth_service import handle_callback, initiate_oauth
from app.services.token_service import create_access_token, create_refresh_token
from app.services.app_service import get_user_roles

router = APIRouter(prefix="/oauth", tags=["oauth"])


@router.get("/google")
async def google_oauth_initiate(app_id: str = Query(...)):
    try:
        url = await initiate_oauth(app_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return RedirectResponse(url=url)


@router.get("/google/callback")
async def google_oauth_callback(code: str = Query(...), state: str = Query(...)):
    s = get_settings()
    try:
        user_id, app_id = await handle_callback(code, state)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=502, detail="Upstream OAuth error")
    roles = await get_user_roles(user_id)
    access_token = create_access_token({"sub": str(user_id), "app_id": app_id, "roles": roles})
    refresh_token = await create_refresh_token(user_id)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": s.AUTH_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "refresh_token": refresh_token,
    }
