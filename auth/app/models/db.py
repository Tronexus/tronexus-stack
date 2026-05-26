from typing import TypedDict
from uuid import UUID
from datetime import datetime


class AppRow(TypedDict):
    id: UUID
    name: str
    description: str | None
    client_id: str
    created_at: datetime


class UserRow(TypedDict):
    id: UUID
    app_id: UUID
    google_id: str
    email: str
    name: str | None
    avatar_url: str | None
    created_at: datetime
    last_login_at: datetime
