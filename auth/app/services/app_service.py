import uuid
from app.db.postgres import get_pool
from app.models.schemas import AppCreate


async def list_apps() -> list[dict]:
    pool = await get_pool()
    rows = await pool.fetch("SELECT * FROM apps ORDER BY created_at DESC")
    return [dict(r) for r in rows]


async def create_app(data: AppCreate) -> dict:
    pool = await get_pool()
    row = await pool.fetchrow(
        "INSERT INTO apps (name, description) VALUES ($1, $2) RETURNING *",
        data.name, data.description,
    )
    return dict(row)


async def list_roles(app_id: uuid.UUID) -> list[dict]:
    pool = await get_pool()
    rows = await pool.fetch("SELECT * FROM roles WHERE app_id = $1 ORDER BY name", app_id)
    return [dict(r) for r in rows]


async def create_role(app_id: uuid.UUID, name: str, description: str | None) -> dict:
    pool = await get_pool()
    row = await pool.fetchrow(
        "INSERT INTO roles (app_id, name, description) VALUES ($1, $2, $3) RETURNING *",
        app_id, name, description,
    )
    return dict(row)


async def assign_role(user_id: uuid.UUID, role_id: uuid.UUID) -> None:
    pool = await get_pool()
    await pool.execute(
        "INSERT INTO user_roles (user_id, role_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
        user_id, role_id,
    )


async def get_user_roles(user_id: uuid.UUID) -> list[str]:
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT r.name FROM roles r JOIN user_roles ur ON ur.role_id = r.id WHERE ur.user_id = $1",
        user_id,
    )
    return [r["name"] for r in rows]
