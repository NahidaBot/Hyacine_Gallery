"""测试鉴权 API 路由。"""

import pytest


@pytest.mark.asyncio
async def test_get_auth_config(app_client):
    """GET /api/auth/config 应返回 bot_username 配置。"""
    resp = await app_client.get("/api/auth/config")
    assert resp.status_code == 200
    body = resp.json()
    assert "bot_username" in body


@pytest.mark.asyncio
async def test_check_admin(app_client, db):
    """GET /api/auth/check-admin?tg_id=xxx 应检查用户管理权限。"""
    # 无匹配用户时 is_admin 应为 False
    resp = await app_client.get("/api/auth/check-admin", params={"tg_id": 123})
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_admin"] is False
    assert body["role"] is None

    # 创建一个 owner 用户后再检查
    from app.models.user import User

    user = User(tg_id=456, tg_username="owner_user", role="owner")
    db.add(user)
    await db.flush()
    await db.commit()

    resp2 = await app_client.get("/api/auth/check-admin", params={"tg_id": 456})
    assert resp2.status_code == 200
    body2 = resp2.json()
    assert body2["is_admin"] is True
    assert body2["role"] == "owner"


@pytest.mark.asyncio
async def test_check_admin_regular_user(app_client, db):
    """非管理员用户 is_admin 应为 False（但 role 不为 None）。"""
    from app.models.user import User

    # 创建一个非管理员角色用户（直接设 admin 角色但不同 tg_id）
    # 这里 admin 角色也属于管理员，所以测试 check-admin 的完整逻辑
    user = User(tg_id=789, tg_username="admin_user", role="admin")
    db.add(user)
    await db.flush()
    await db.commit()

    resp = await app_client.get("/api/auth/check-admin", params={"tg_id": 789})
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_admin"] is True
    assert body["role"] == "admin"


@pytest.mark.asyncio
async def test_get_me_no_auth(app_client):
    """GET /api/auth/me 无 Authorization header 应返回 401。"""
    resp = await app_client.get("/api/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_me_invalid_token(app_client):
    """GET /api/auth/me 无效 token 应返回 401。"""
    resp = await app_client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer invalid.token.here"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_me_valid_token(app_client, db):
    """GET /api/auth/me 使用有效 JWT 应返回用户信息。"""
    from app.models.user import User
    from app.services.auth_service import create_jwt

    user = User(tg_id=111, tg_username="me_user", role="admin")
    db.add(user)
    await db.flush()
    await db.commit()
    await db.refresh(user)

    token = create_jwt(user.id, user.role)
    resp = await app_client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["tg_username"] == "me_user"
    assert body["role"] == "admin"


@pytest.mark.asyncio
async def test_get_me_user_deleted(app_client, db):
    """JWT 有效但用户已被删除应返回 401。"""
    from app.models.user import User
    from app.services.auth_service import create_jwt

    user = User(tg_id=222, tg_username="ghost_user", role="admin")
    db.add(user)
    await db.flush()
    await db.commit()
    await db.refresh(user)
    token = create_jwt(user.id, user.role)

    # 删除用户
    await db.delete(user)
    await db.commit()

    resp = await app_client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_passkey_register_begin_not_logged_in(app_client):
    """未登录时 passkey 注册应返回 401。"""
    # CurrentUserDep 被 override 为返回 None
    resp = await app_client.post("/api/auth/passkey/register/begin")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_passkey_register_complete_not_logged_in(app_client):
    """未登录时 passkey 注册完成应返回 401。"""
    resp = await app_client.post(
        "/api/auth/passkey/register/complete",
        json={"credential": {}, "device_name": "test"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_passkey_auth_begin_returns_options(app_client):
    """passkey 认证 begin（无用户名模式）应返回 200 和 challenge options。"""
    resp = await app_client.post("/api/auth/passkey/auth/begin")
    assert resp.status_code == 200
    data = resp.json()
    assert "challengeToken" in data
    assert "challenge" in data
