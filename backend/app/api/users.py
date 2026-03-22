"""站长专属用户管理路由。"""

from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentUserDep, DBDep, OwnerDep
from app.models.artwork import Artwork, BotPostLog
from app.models.user import User
from app.models.webauthn import WebAuthnCredential

router = APIRouter(dependencies=[OwnerDep])


# ── Pydantic 模型 ──────────────────────────────────────────────────────────────


class UserResponse(BaseModel):
    id: int
    tg_id: int | None
    tg_username: str
    email: str | None
    role: str
    created_at: datetime
    last_login_at: datetime | None
    import_count: int
    post_count: int

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    tg_id: int | None = None
    tg_username: str = ""
    email: str | None = None
    role: str = "admin"


class UserUpdate(BaseModel):
    tg_username: str | None = None
    email: str | None = None
    role: str | None = None


class PasskeyCredentialResponse(BaseModel):
    id: int
    credential_id: str
    device_name: str
    sign_count: int
    created_at: datetime
    last_used_at: datetime | None

    model_config = {"from_attributes": True}


# ── 工具 ──────────────────────────────────────────────────────────────────────


async def _fetch_user_with_stats(db: AsyncSession, user: User) -> UserResponse:
    import_result = await db.execute(
        select(func.count()).select_from(Artwork).where(Artwork.imported_by_id == user.id)
    )
    import_count: int = import_result.scalar_one()

    post_result = await db.execute(
        select(func.count()).select_from(BotPostLog).where(BotPostLog.posted_by_user_id == user.id)
    )
    post_count: int = post_result.scalar_one()

    return UserResponse(
        id=user.id,
        tg_id=user.tg_id,
        tg_username=user.tg_username,
        email=user.email,
        role=user.role,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
        import_count=import_count,
        post_count=post_count,
    )


# ── 用户 CRUD ──────────────────────────────────────────────────────────────────


@router.get("", response_model=list[UserResponse])
async def list_users(db: AsyncSession = DBDep) -> list[UserResponse]:
    """列出所有用户及统计信息。"""
    result = await db.execute(select(User).order_by(User.id))
    users = list(result.scalars().all())
    return [await _fetch_user_with_stats(db, u) for u in users]


@router.post("", response_model=UserResponse)
async def create_user(data: UserCreate, db: AsyncSession = DBDep) -> UserResponse:
    """创建新用户（站长手动添加，无需 Telegram 登录）。"""
    if data.role not in ("admin", "owner"):
        raise HTTPException(400, "role 只能是 admin 或 owner")

    user = User(
        tg_id=data.tg_id,
        tg_username=data.tg_username,
        email=data.email,
        role=data.role,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    await db.commit()
    return await _fetch_user_with_stats(db, user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    data: UserUpdate,
    current_user: User | None = CurrentUserDep,
    db: AsyncSession = DBDep,
) -> UserResponse:
    """更新用户信息。不允许降低自己的权限。"""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "用户不存在")

    # 防止站长降低自己权限
    if current_user and user.id == current_user.id and data.role and data.role != "owner":
        raise HTTPException(400, "不能修改自己的权限")

    if data.tg_username is not None:
        user.tg_username = data.tg_username
    if data.email is not None:
        user.email = data.email or None  # 空字符串转 None
    if data.role is not None:
        if data.role not in ("admin", "owner"):
            raise HTTPException(400, "role 只能是 admin 或 owner")
        user.role = data.role

    await db.commit()
    await db.refresh(user)
    return await _fetch_user_with_stats(db, user)


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User | None = CurrentUserDep,
    db: AsyncSession = DBDep,
) -> dict[str, str]:
    """删除用户。不允许删除自己。"""
    if current_user and user_id == current_user.id:
        raise HTTPException(400, "不能删除自己")

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "用户不存在")

    await db.delete(user)
    await db.commit()
    return {"status": "deleted"}


# ── Passkey 凭据管理（管理员查看 / 删除其他用户的凭据） ────────────────────────


@router.get("/{user_id}/credentials", response_model=list[PasskeyCredentialResponse])
async def list_user_credentials(
    user_id: int, db: AsyncSession = DBDep
) -> list[PasskeyCredentialResponse]:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "用户不存在")

    result = await db.execute(
        select(WebAuthnCredential)
        .where(WebAuthnCredential.user_id == user_id)
        .order_by(WebAuthnCredential.created_at)
    )
    creds = list(result.scalars().all())
    return [PasskeyCredentialResponse.model_validate(c) for c in creds]


@router.delete("/{user_id}/credentials/{cred_id}")
async def delete_user_credential(
    user_id: int, cred_id: int, db: AsyncSession = DBDep
) -> dict[str, str]:
    cred = await db.get(WebAuthnCredential, cred_id)
    if not cred or cred.user_id != user_id:
        raise HTTPException(404, "凭据不存在")

    await db.delete(cred)
    await db.commit()
    return {"status": "deleted"}
