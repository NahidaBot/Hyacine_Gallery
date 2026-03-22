import hmac
from collections.abc import AsyncGenerator

import jwt as pyjwt
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.services.auth_service import decode_jwt


async def get_session() -> AsyncGenerator[AsyncSession]:
    async for session in get_db():
        yield session


async def require_admin(request: Request) -> None:
    """双轨鉴权：优先 JWT Bearer token，回退静态 X-Admin-Token（供 bot 和旧客户端使用）。"""
    # 1. 优先：Authorization: Bearer <jwt>
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        try:
            decode_jwt(token)
            return
        except pyjwt.InvalidTokenError:
            pass

    # 2. 回退：X-Admin-Token header 或 admin_token cookie（bot / 旧前端兼容）
    static_token = request.headers.get("X-Admin-Token") or request.cookies.get("admin_token")
    if (
        static_token
        and settings.admin_token
        and hmac.compare_digest(static_token, settings.admin_token)
    ):
        return

    raise HTTPException(status_code=401, detail="未授权")


async def get_current_user(request: Request, db: AsyncSession = Depends(get_session)):  # type: ignore[return]  # noqa: B008
    """从 JWT 解析当前用户；静态 token 或无 token 时返回 None。"""
    from app.models.user import User

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[7:]
    try:
        payload = decode_jwt(token)
        user_id = int(str(payload["sub"]))
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
    except pyjwt.InvalidTokenError, KeyError, ValueError:
        return None


async def require_owner(request: Request) -> None:
    """仅允许 role == 'owner' 的用户访问。"""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=403, detail="需要站长权限")
    token = auth_header[7:]
    try:
        payload = decode_jwt(token)
        if payload.get("role") != "owner":
            raise HTTPException(status_code=403, detail="需要站长权限")
    except pyjwt.InvalidTokenError as e:
        raise HTTPException(status_code=403, detail="需要站长权限") from e


AdminDep = Depends(require_admin)
OwnerDep = Depends(require_owner)
DBDep = Depends(get_session)
CurrentUserDep = Depends(get_current_user)
