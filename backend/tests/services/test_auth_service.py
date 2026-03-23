"""auth_service 单元测试。"""

import hashlib
import hmac
import time

import jwt
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.auth_service import create_jwt, decode_jwt, verify_telegram_login


@pytest.fixture(autouse=True)
def _patch_settings(monkeypatch):
    """为所有测试设置默认 JWT/Telegram 配置。"""
    import app.config

    monkeypatch.setattr(app.config.settings, "jwt_secret", "test-jwt-secret-key")
    monkeypatch.setattr(app.config.settings, "jwt_expire_hours", 1)
    monkeypatch.setattr(
        app.config.settings, "telegram_bot_token", "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    )


def _make_telegram_data(bot_token: str, **extra_fields: str) -> dict[str, str]:
    """构造带有效 HMAC 签名的 Telegram Login Widget 数据。"""
    data: dict[str, str] = {
        "id": "12345",
        "first_name": "Test",
        "username": "testuser",
        "auth_date": str(int(time.time())),
        **extra_fields,
    }
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    check_string = "\n".join(sorted(f"{k}={v}" for k, v in data.items()))
    data["hash"] = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()
    return data


# ── JWT ──


async def test_create_and_decode_jwt(db: AsyncSession):
    token = create_jwt(user_id=42, role="admin")
    payload = decode_jwt(token)
    assert payload["sub"] == "42"
    assert payload["role"] == "admin"
    assert "exp" in payload


async def test_decode_jwt_expired(db: AsyncSession, monkeypatch):
    import app.config

    monkeypatch.setattr(app.config.settings, "jwt_expire_hours", 0)
    # jwt_expire_hours=0 → exp = now + 0 = now，即刻过期
    token = create_jwt(user_id=1, role="viewer")
    # 等待一秒以确保过期
    import time as _time

    _time.sleep(1)
    with pytest.raises(jwt.InvalidTokenError):
        decode_jwt(token)


async def test_decode_jwt_bad_secret(db: AsyncSession, monkeypatch):
    token = create_jwt(user_id=1, role="admin")

    import app.config

    monkeypatch.setattr(app.config.settings, "jwt_secret", "different-secret-key")
    with pytest.raises(jwt.InvalidTokenError):
        decode_jwt(token)


# ── Telegram Login ──


async def test_verify_telegram_login_no_token(db: AsyncSession, monkeypatch):
    import app.config

    monkeypatch.setattr(app.config.settings, "telegram_bot_token", "")
    with pytest.raises(ValueError, match="未配置"):
        verify_telegram_login({"id": "1", "hash": "abc"})


async def test_verify_telegram_login_no_hash(db: AsyncSession):
    with pytest.raises(ValueError, match="hash"):
        verify_telegram_login({"id": "1", "first_name": "Test"})


async def test_verify_telegram_login_valid(db: AsyncSession):
    bot_token = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    data = _make_telegram_data(bot_token)

    user = verify_telegram_login(data)
    assert user.id == 12345
    assert user.username == "testuser"
    assert user.first_name == "Test"


async def test_verify_telegram_login_bad_hash(db: AsyncSession):
    bot_token = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    data = _make_telegram_data(bot_token)
    data["hash"] = "0" * 64  # 错误的哈希

    with pytest.raises(ValueError, match="签名验证失败"):
        verify_telegram_login(data)


async def test_verify_telegram_login_expired(db: AsyncSession):
    bot_token = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    data = _make_telegram_data(bot_token, auth_date=str(int(time.time()) - 600))

    with pytest.raises(ValueError, match="过期"):
        verify_telegram_login(data)
