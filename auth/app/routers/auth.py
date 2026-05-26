import uuid
from fastapi import APIRouter, Depends, HTTPException

from app.config import get_settings
from app.db.postgres import get_pool
from app.dependencies import get_current_user
from app.models.schemas import RefreshRequest, TokenResponse, UserProfile
from app.services.app_service import get_user_roles
from app.services.token_service import create_access_token, revoke_user_tokens, rotate_refresh_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest):
    s = get_settings()
    try:
        new_refresh, user_id = await rotate_refresh_token(body.refresh_token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    pool = await get_pool()
    user = await pool.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    roles = await get_user_roles(user_id)
    access_token = create_access_token({"sub": str(user_id), "app_id": str(user["app_id"]), "roles": roles})
    return TokenResponse(access_token=access_token, expires_in=s.AUTH_ACCESS_TOKEN_EXPIRE_MINUTES * 60, refresh_token=new_refresh)


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    await revoke_user_tokens(uuid.UUID(current_user["sub"]))
    return {"detail": "Logged out"}


@router.get("/me", response_model=UserProfile)
async def get_me(current_user: dict = Depends(get_current_user)):
    user_id = uuid.UUID(current_user["sub"])
    pool = await get_pool()
    user = await pool.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserProfile(
        id=user["id"], app_id=user["app_id"], email=user["email"],
        name=user["name"], avatar_url=user["avatar_url"],
        roles=await get_user_roles(user_id),
        created_at=user["created_at"], last_login_at=user["last_login_at"],
    )
