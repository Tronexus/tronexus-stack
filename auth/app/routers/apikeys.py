import uuid
from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import require_admin_api_key
from app.models.schemas import ApiKeyCreate, ApiKeyCreated, ApiKeyVerifyClaims, ApiKeyVerifyRequest
from app.services.apikey_service import create_api_key, revoke_api_key, verify_api_key

router = APIRouter(prefix="/apikeys", tags=["apikeys"])


@router.post("", response_model=ApiKeyCreated)
async def create_key(data: ApiKeyCreate, _: dict = Depends(require_admin_api_key)):
    result = await create_api_key(data)
    return ApiKeyCreated(
        id=result["id"], app_id=result["app_id"], name=result["name"],
        scopes=result["scopes"], expires_at=result["expires_at"],
        last_used_at=result["last_used_at"], created_at=result["created_at"],
        key=result["key"],
    )


@router.delete("/{key_id}")
async def revoke_key(key_id: uuid.UUID, _: dict = Depends(require_admin_api_key)):
    if not await revoke_api_key(key_id):
        raise HTTPException(status_code=404, detail="Key not found or already revoked")
    return {"detail": "Key revoked"}


@router.post("/verify", response_model=ApiKeyVerifyClaims)
async def verify_key(body: ApiKeyVerifyRequest):
    result = await verify_api_key(body.key)
    if result is None:
        raise HTTPException(status_code=401, detail="Invalid or expired API key")
    return ApiKeyVerifyClaims(
        app_id=result["app_id"], key_id=result["id"], name=result["name"],
        scopes=result["scopes"], expires_at=result["expires_at"],
    )
