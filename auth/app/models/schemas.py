from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime


class AppCreate(BaseModel):
    name: str
    description: str | None = None


class AppResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    client_id: str
    created_at: datetime


class RoleCreate(BaseModel):
    name: str
    description: str | None = None


class RoleResponse(BaseModel):
    id: UUID
    app_id: UUID
    name: str
    description: str | None


class RoleAssign(BaseModel):
    role_id: UUID


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UserProfile(BaseModel):
    id: UUID
    app_id: UUID
    email: str
    name: str | None
    avatar_url: str | None
    roles: list[str]
    created_at: datetime
    last_login_at: datetime


class ApiKeyCreate(BaseModel):
    app_id: UUID
    name: str
    scopes: list[str] = Field(default_factory=list)
    expires_in_days: int = Field(ge=1, le=365)


class ApiKeyResponse(BaseModel):
    id: UUID
    app_id: UUID
    name: str
    scopes: list[str]
    expires_at: datetime
    last_used_at: datetime | None
    created_at: datetime


class ApiKeyCreated(ApiKeyResponse):
    key: str


class ApiKeyVerifyRequest(BaseModel):
    key: str


class ApiKeyVerifyClaims(BaseModel):
    app_id: UUID
    key_id: UUID
    name: str
    scopes: list[str]
    expires_at: datetime


class HealthResponse(BaseModel):
    status: str = "ok"
