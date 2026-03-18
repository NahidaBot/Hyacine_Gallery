import hmac
from collections.abc import AsyncGenerator

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db


async def get_session() -> AsyncGenerator[AsyncSession]:
    async for session in get_db():
        yield session


async def require_admin(request: Request) -> None:
    token = request.headers.get("X-Admin-Token") or request.cookies.get("admin_token")
    if not token or not hmac.compare_digest(token, settings.admin_token):
        raise HTTPException(status_code=401, detail="Unauthorized")


AdminDep = Depends(require_admin)
DBDep = Depends(get_session)
