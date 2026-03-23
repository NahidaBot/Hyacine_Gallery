"""WebAuthn Passkeys 注册与认证服务（封装 py_webauthn）。"""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Any

import jwt
import webauthn
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from app.config import settings

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.webauthn import WebAuthnCredential


def _rp_id() -> str:
    return settings.webauthn_rp_id


def _origin() -> str:
    return settings.webauthn_origin


# ── Challenge Token ──────────────────────────────────────────────────────────
# 无用户名认证流程中，begin 阶段不知道用户是谁，无法将 challenge 存在 User 记录上。
# 改用签名的短期 JWT 来传递 challenge，complete 时由前端带回。


def create_challenge_token(challenge_b64: str) -> str:
    """将 challenge 打包为签名的短期 JWT（5 分钟有效）。"""
    payload = {
        "challenge": challenge_b64,
        "exp": int(time.time()) + 300,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def verify_challenge_token(token: str) -> str:
    """验证 challenge token，返回 challenge_b64。过期或篡改时抛异常。"""
    payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    return str(payload["challenge"])


def user_handle_to_id(user_handle_b64: str) -> int:
    """将 base64url 编码的 userHandle 解码为用户 ID。"""
    raw = base64url_to_bytes(user_handle_b64)
    return int.from_bytes(raw, "big")


# ── 注册（Registration） ─────────────────────────────────────────────────────


def begin_registration(user: User) -> tuple[dict[str, Any], str]:
    """生成注册 options，返回 (options_dict, challenge_b64url)。"""
    options = webauthn.generate_registration_options(
        rp_id=_rp_id(),
        rp_name=settings.webauthn_rp_name,
        user_id=user.id.to_bytes(8, "big"),
        user_name=user.tg_username or user.email or f"user_{user.id}",
        user_display_name=user.tg_username or user.email or f"User {user.id}",
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.REQUIRED,
            user_verification=UserVerificationRequirement.PREFERRED,
        ),
    )
    challenge_b64 = bytes_to_base64url(options.challenge)
    return json.loads(webauthn.options_to_json(options)), challenge_b64


def complete_registration(
    response_json: dict,  # type: ignore[type-arg]
    challenge_b64: str,
    device_name: str = "",
) -> tuple[str, str, int]:
    """验证注册 response，返回 (credential_id_b64, public_key_b64, sign_count)。"""
    challenge = base64url_to_bytes(challenge_b64)
    verification = webauthn.verify_registration_response(
        credential=response_json,
        expected_challenge=challenge,
        expected_rp_id=_rp_id(),
        expected_origin=_origin(),
    )
    credential_id_b64 = bytes_to_base64url(verification.credential_id)
    public_key_b64 = bytes_to_base64url(verification.credential_public_key)
    return credential_id_b64, public_key_b64, verification.sign_count


# ── 认证（Authentication） ───────────────────────────────────────────────────


def begin_authentication() -> tuple[dict, str]:  # type: ignore[type-arg]
    """生成无用户名认证 options（空 allowCredentials），返回 (options_dict, challenge_b64url)。"""
    options = webauthn.generate_authentication_options(
        rp_id=_rp_id(),
        allow_credentials=[],
        user_verification=UserVerificationRequirement.PREFERRED,
    )
    challenge_b64 = bytes_to_base64url(options.challenge)
    return json.loads(webauthn.options_to_json(options)), challenge_b64


def complete_authentication(
    response_json: dict,  # type: ignore[type-arg]
    credential: WebAuthnCredential,
    challenge_b64: str,
) -> int:
    """验证认证 response。返回新 sign_count（调用方需写回 DB）。"""
    challenge = base64url_to_bytes(challenge_b64)
    verification = webauthn.verify_authentication_response(
        credential=response_json,
        expected_challenge=challenge,
        expected_rp_id=_rp_id(),
        expected_origin=_origin(),
        credential_public_key=base64url_to_bytes(credential.public_key),
        credential_current_sign_count=credential.sign_count,
    )
    return verification.new_sign_count
