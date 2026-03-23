"""Telegram OAuth + WebAuthn Passkeys + JWT 鉴权路由。"""

from datetime import UTC, datetime

import jwt as pyjwt
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import AdminDep, CurrentUserDep, DBDep
from app.config import settings
from app.models.user import User
from app.models.webauthn import WebAuthnCredential
from app.services import webauthn_service
from app.services.auth_service import TelegramUser, create_jwt, decode_jwt, verify_telegram_login

router = APIRouter()


# ── Pydantic 模型 ──────────────────────────────────────────────────────────────


class TelegramAuthRequest(BaseModel):
    id: int
    first_name: str = ""
    last_name: str = ""
    username: str = ""
    photo_url: str = ""
    auth_date: int
    hash: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class UserResponse(BaseModel):
    id: int
    tg_id: int | None
    tg_username: str
    email: str | None
    role: str


class AdminCheckResponse(BaseModel):
    is_admin: bool
    role: str | None


class PasskeyRegisterBeginResponse(BaseModel):
    options: dict  # type: ignore[type-arg]


class PasskeyRegisterCompleteRequest(BaseModel):
    credential: dict  # type: ignore[type-arg]
    device_name: str = ""


class PasskeyAuthCompleteRequest(BaseModel):
    credential: dict  # type: ignore[type-arg]
    challenge_token: str


# ── 工具 ──────────────────────────────────────────────────────────────────────


def _now_utc() -> datetime:
    return datetime.now(UTC)


# ── 路由 ──────────────────────────────────────────────────────────────────────


@router.get("/config")
async def get_auth_config() -> dict[str, str]:
    return {"bot_username": settings.telegram_bot_username}


@router.post("/telegram", response_model=TokenResponse)
async def telegram_login(body: TelegramAuthRequest, db: AsyncSession = DBDep) -> TokenResponse:
    """验证 Telegram Login Widget 回调，upsert User 记录，颁发 JWT。"""
    raw: dict[str, str] = {
        k: str(v)
        for k, v in body.model_dump().items()
        if v not in ("", None, 0) or k in ("id", "auth_date", "hash")
    }
    try:
        tg_user: TelegramUser = verify_telegram_login(raw)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e

    result = await db.execute(select(User).where(User.tg_id == tg_user.id))
    user = result.scalar_one_or_none()

    if user is None:
        count_result = await db.execute(select(func.count()).select_from(User))
        user_count: int = count_result.scalar_one()
        if user_count > 0:
            raise HTTPException(status_code=403, detail="无访问权限。请联系站长将你添加为管理员。")
        user = User(tg_id=tg_user.id, tg_username=tg_user.username, role="owner")
        db.add(user)
    else:
        user.tg_username = tg_user.username

    user.last_login_at = _now_utc()
    await db.flush()
    await db.refresh(user)
    await db.commit()

    token = create_jwt(user.id, user.role)
    return TokenResponse(access_token=token, role=user.role)


@router.get("/me", response_model=UserResponse)
async def get_me(request: Request, db: AsyncSession = DBDep) -> UserResponse:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未授权")
    token = auth_header[7:]
    try:
        payload = decode_jwt(token)
    except pyjwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail="Token 无效或已过期") from e

    user_id = int(str(payload["sub"]))
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")

    return UserResponse(
        id=user.id, tg_id=user.tg_id, tg_username=user.tg_username, email=user.email, role=user.role
    )


@router.get("/check-admin", response_model=AdminCheckResponse, dependencies=[AdminDep])
async def check_admin(tg_id: int, db: AsyncSession = DBDep) -> AdminCheckResponse:
    result = await db.execute(select(User).where(User.tg_id == tg_id))
    user = result.scalar_one_or_none()
    if user and user.role in ("owner", "admin"):
        return AdminCheckResponse(is_admin=True, role=user.role)
    return AdminCheckResponse(is_admin=False, role=user.role if user else None)


# ── Passkey 注册（需已登录） ────────────────────────────────────────────────────


@router.post("/passkey/register/begin")
async def passkey_register_begin(
    current_user: User | None = CurrentUserDep,
    db: AsyncSession = DBDep,
) -> dict:  # type: ignore[type-arg]
    """为已登录用户生成 passkey 注册 options。"""
    if not current_user:
        raise HTTPException(status_code=401, detail="未登录")

    options, challenge_b64 = webauthn_service.begin_registration(current_user)
    current_user.webauthn_challenge = challenge_b64
    await db.commit()
    return options


@router.post("/passkey/register/complete")
async def passkey_register_complete(
    body: PasskeyRegisterCompleteRequest,
    current_user: User | None = CurrentUserDep,
    db: AsyncSession = DBDep,
) -> dict[str, str]:
    """验证注册 response，存储凭据。"""
    if not current_user:
        raise HTTPException(status_code=401, detail="未登录")
    if not current_user.webauthn_challenge:
        raise HTTPException(status_code=400, detail="无有效的注册会话，请重新开始")

    try:
        cred_id_b64, pub_key_b64, sign_count = webauthn_service.complete_registration(
            body.credential, current_user.webauthn_challenge, body.device_name
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"注册验证失败：{e}") from e

    credential = WebAuthnCredential(
        user_id=current_user.id,
        credential_id=cred_id_b64,
        public_key=pub_key_b64,
        sign_count=sign_count,
        device_name=body.device_name or "未命名设备",
    )
    db.add(credential)
    current_user.webauthn_challenge = None
    await db.commit()
    return {"status": "ok"}


# ── Passkey 认证（无需登录，无需输入用户名） ─────────────────────────────────────


@router.post("/passkey/auth/begin")
async def passkey_auth_begin() -> dict:  # type: ignore[type-arg]
    """生成无用户名认证 options，challenge 通过签名 token 传递。"""
    options, challenge_b64 = webauthn_service.begin_authentication()
    challenge_token = webauthn_service.create_challenge_token(challenge_b64)
    return {**options, "challengeToken": challenge_token}


@router.post("/passkey/auth/complete", response_model=TokenResponse)
async def passkey_auth_complete(
    body: PasskeyAuthCompleteRequest,
    db: AsyncSession = DBDep,
) -> TokenResponse:
    """验证认证 response，通过 userHandle 识别用户，颁发 JWT。"""
    # 验证 challenge token
    try:
        challenge_b64 = webauthn_service.verify_challenge_token(body.challenge_token)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Challenge 无效或已过期：{e}") from e

    # 通过 userHandle 识别用户
    user_handle = body.credential.get("response", {}).get("userHandle")
    if not user_handle:
        raise HTTPException(status_code=400, detail="凭据缺少 userHandle，无法识别用户")

    try:
        user_id = webauthn_service.user_handle_to_id(user_handle)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"userHandle 解析失败：{e}") from e

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=400, detail="用户不存在")

    # 找到匹配的凭据
    credential_id = body.credential.get("id", "")
    cred_result = await db.execute(
        select(WebAuthnCredential).where(
            WebAuthnCredential.credential_id == credential_id,
            WebAuthnCredential.user_id == user.id,
        )
    )
    credential = cred_result.scalar_one_or_none()
    if not credential:
        raise HTTPException(status_code=400, detail="凭据不存在")

    try:
        new_sign_count = webauthn_service.complete_authentication(
            body.credential, credential, challenge_b64
        )
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Passkey 验证失败：{e}") from e

    credential.sign_count = new_sign_count
    credential.last_used_at = _now_utc()
    user.last_login_at = _now_utc()
    await db.commit()

    token = create_jwt(user.id, user.role)
    return TokenResponse(access_token=token, role=user.role)
