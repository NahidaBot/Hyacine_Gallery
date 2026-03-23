"""Telegram Login Widget 验证 + JWT 颁发/解析。"""

import hashlib
import hmac
import time
from dataclasses import dataclass

import jwt

from app.config import settings


@dataclass
class TelegramUser:
    id: int
    username: str
    first_name: str
    auth_date: int


def verify_telegram_login(data: dict[str, str]) -> TelegramUser:
    """验证 Telegram Login Widget 回调数据的 HMAC 签名。

    Telegram 规范：
      secret_key  = SHA256(bot_token)（注意不是 HMAC，是直接哈希）
      check_string = 所有字段（排除 hash）按字母序 "key=value" 以 \\n 连接
      expected    = HMAC-SHA256(check_string, secret_key).hexdigest()

    成功返回 TelegramUser，失败抛 ValueError。
    """
    if not settings.telegram_bot_token:
        raise ValueError("未配置 TELEGRAM_BOT_TOKEN，无法验证 Telegram 登录")

    received_hash = data.get("hash", "")
    if not received_hash:
        raise ValueError("回调数据缺少 hash 字段")

    # 按字母序构造 check_string（排除 hash 字段）
    check_fields = sorted(
        (f"{k}={v}" for k, v in data.items() if k != "hash"),
    )
    check_string = "\n".join(check_fields)

    secret_key = hashlib.sha256(settings.telegram_bot_token.encode()).digest()
    expected_hash = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_hash, received_hash):
        raise ValueError("Telegram 签名验证失败")

    # 检查时效（300 秒 = 5 分钟，防重放攻击）
    auth_date = int(data.get("auth_date", 0))
    if time.time() - auth_date > 300:
        raise ValueError("Telegram 登录已过期（超过 5 分钟）")

    return TelegramUser(
        id=int(data["id"]),
        username=data.get("username", ""),
        first_name=data.get("first_name", ""),
        auth_date=auth_date,
    )


def create_jwt(user_id: int, role: str) -> str:
    """颁发 HS256 JWT。Payload: {sub, role, exp}"""
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": int(time.time()) + settings.jwt_expire_hours * 3600,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_jwt(token: str) -> dict[str, object]:
    """解析并验证 JWT。失败抛 jwt.InvalidTokenError。"""
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
