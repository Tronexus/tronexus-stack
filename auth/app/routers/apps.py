import uuid
from asyncpg import UniqueViolationError
from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_current_user, require_admin_api_key
from app.models.schemas import AppCreate, AppResponse, RoleAssign, RoleCreate, RoleResponse
from app.services.app_service import assign_role, create_app, create_role, list_apps, list_roles

router = APIRouter(prefix="/apps", tags=["apps"])


@router.get("", response_model=list[AppResponse])
async def get_apps(_: dict = Depends(require_admin_api_key)):
    return await list_apps()


@router.post("", response_model=AppResponse)
async def register_app(data: AppCreate, _: dict = Depends(require_admin_api_key)):
    try:
        return await create_app(data)
    except UniqueViolationError:
        raise HTTPException(status_code=409, detail="App name already exists")


@router.get("/{app_id}/roles", response_model=list[RoleResponse])
async def get_roles(app_id: uuid.UUID, _: dict = Depends(get_current_user)):
    return await list_roles(app_id)


@router.post("/{app_id}/roles", response_model=RoleResponse)
async def add_role(app_id: uuid.UUID, data: RoleCreate, _: dict = Depends(require_admin_api_key)):
    try:
        return await create_role(app_id, data.name, data.description)
    except UniqueViolationError:
        raise HTTPException(status_code=409, detail="Role already exists for this app")


@router.post("/{app_id}/users/{user_id}/roles")
async def assign_user_role(app_id: uuid.UUID, user_id: uuid.UUID, data: RoleAssign, _: dict = Depends(require_admin_api_key)):
    await assign_role(user_id, data.role_id)
    return {"detail": "Role assigned"}
