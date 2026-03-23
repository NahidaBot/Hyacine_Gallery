"""测试鉴权依赖函数（不使用 test override，直接调用函数）。"""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.api.dependencies import require_admin, require_owner
from app.config import settings
from app.services.auth_service import create_jwt


def _make_request(
    *,
    headers: dict[str, str] | None = None,
    cookies: dict[str, str] | None = None,
) -> MagicMock:
    """构造模拟 Request 对象。"""
    _headers = headers or {}
    _cookies = cookies or {}
    request = MagicMock()
    request.headers = MagicMock()
    request.headers.get = MagicMock(side_effect=lambda key, default="": _headers.get(key, default))
    request.cookies = MagicMock()
    request.cookies.get = MagicMock(
        side_effect=lambda key, default=None: _cookies.get(key, default)
    )
    return request


async def test_require_admin_jwt():
    """有效 JWT Bearer token 应通过鉴权。"""
    token = create_jwt(user_id=1, role="admin")
    request = _make_request(headers={"Authorization": f"Bearer {token}"})
    await require_admin(request)


async def test_require_admin_static_token():
    """X-Admin-Token header 匹配静态 token 应通过鉴权。"""
    request = _make_request(headers={"X-Admin-Token": settings.admin_token})
    await require_admin(request)


async def test_require_admin_cookie():
    """admin_token cookie 匹配静态 token 应通过鉴权。"""
    request = _make_request(cookies={"admin_token": settings.admin_token})
    await require_admin(request)


async def test_require_admin_fails():
    """无任何鉴权信息应抛出 401。"""
    request = _make_request()
    with pytest.raises(HTTPException) as exc_info:
        await require_admin(request)
    assert exc_info.value.status_code == 401


async def test_require_admin_bad_jwt():
    """无效 JWT 且无静态 token 应抛出 401。"""
    request = _make_request(headers={"Authorization": "Bearer invalid.token.here"})
    with pytest.raises(HTTPException) as exc_info:
        await require_admin(request)
    assert exc_info.value.status_code == 401


async def test_require_owner():
    """role=owner 的 JWT 应通过 require_owner。"""
    token = create_jwt(user_id=1, role="owner")
    request = _make_request(headers={"Authorization": f"Bearer {token}"})
    await require_owner(request)


async def test_require_owner_not_owner():
    """role=admin 的 JWT 应被 require_owner 拒绝（403）。"""
    token = create_jwt(user_id=1, role="admin")
    request = _make_request(headers={"Authorization": f"Bearer {token}"})
    with pytest.raises(HTTPException) as exc_info:
        await require_owner(request)
    assert exc_info.value.status_code == 403


async def test_require_owner_no_token():
    """无 token 应被 require_owner 拒绝（403）。"""
    request = _make_request()
    with pytest.raises(HTTPException) as exc_info:
        await require_owner(request)
    assert exc_info.value.status_code == 403
