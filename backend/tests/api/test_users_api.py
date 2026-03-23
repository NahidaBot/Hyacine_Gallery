"""测试用户管理 API 路由。"""

import pytest


@pytest.mark.asyncio
async def test_list_users(app_client):
    """GET /api/admin/users 应返回用户列表。"""
    resp = await app_client.get("/api/admin/users")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)


@pytest.mark.asyncio
async def test_create_user(app_client):
    """POST /api/admin/users 应创建用户。"""
    resp = await app_client.post(
        "/api/admin/users",
        json={
            "tg_id": 111222333,
            "tg_username": "new_admin",
            "role": "admin",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["tg_id"] == 111222333
    assert body["tg_username"] == "new_admin"
    assert body["role"] == "admin"


@pytest.mark.asyncio
async def test_update_user(app_client, db):
    """PUT /api/admin/users/{id} 应更新用户信息。"""
    from app.models.user import User

    user = User(tg_id=999, tg_username="edit_me", role="admin")
    db.add(user)
    await db.flush()
    await db.commit()
    await db.refresh(user)

    resp = await app_client.put(
        f"/api/admin/users/{user.id}",
        json={"tg_username": "edited_user"},
    )
    assert resp.status_code == 200
    assert resp.json()["tg_username"] == "edited_user"


@pytest.mark.asyncio
async def test_delete_user(app_client, db):
    """DELETE /api/admin/users/{id} 应删除用户。"""
    from app.models.user import User

    user = User(tg_id=888, tg_username="delete_me", role="admin")
    db.add(user)
    await db.flush()
    await db.commit()
    await db.refresh(user)

    resp = await app_client.delete(f"/api/admin/users/{user.id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "deleted"


@pytest.mark.asyncio
async def test_update_user_not_found(app_client):
    """更新不存在的用户应返回 404。"""
    resp = await app_client.put(
        "/api/admin/users/99999",
        json={"tg_username": "x"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_user_not_found(app_client):
    """删除不存在的用户应返回 404。"""
    resp = await app_client.delete("/api/admin/users/99999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_user_invalid_role(app_client):
    """创建用户时使用无效 role 应返回 400。"""
    resp = await app_client.post(
        "/api/admin/users",
        json={
            "tg_id": 555,
            "tg_username": "bad_role",
            "role": "superuser",
        },
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_update_user_invalid_role(app_client, db):
    """更新用户时使用无效 role 应返回 400。"""
    from app.models.user import User

    user = User(tg_id=777, tg_username="role_test", role="admin")
    db.add(user)
    await db.flush()
    await db.commit()
    await db.refresh(user)

    resp = await app_client.put(
        f"/api/admin/users/{user.id}",
        json={"role": "superuser"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_create_user_owner(app_client):
    """创建 owner 角色的用户应成功。"""
    resp = await app_client.post(
        "/api/admin/users",
        json={
            "tg_id": 666,
            "tg_username": "new_owner",
            "role": "owner",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["role"] == "owner"


@pytest.mark.asyncio
async def test_list_users_with_stats(app_client, db):
    """列出用户应包含 import_count 和 post_count 统计。"""
    from app.models.user import User

    user = User(tg_id=333, tg_username="stats_user", role="admin")
    db.add(user)
    await db.flush()
    await db.commit()

    resp = await app_client.get("/api/admin/users")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) >= 1
    for u in body:
        assert "import_count" in u
        assert "post_count" in u
        assert u["import_count"] >= 0
        assert u["post_count"] >= 0


@pytest.mark.asyncio
async def test_list_user_credentials(app_client, db):
    """GET /api/admin/users/{id}/credentials 应返回凭据列表。"""
    from app.models.user import User

    user = User(tg_id=444, tg_username="cred_user", role="admin")
    db.add(user)
    await db.flush()
    await db.commit()
    await db.refresh(user)

    resp = await app_client.get(f"/api/admin/users/{user.id}/credentials")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)


@pytest.mark.asyncio
async def test_list_credentials_user_not_found(app_client):
    """不存在的用户凭据列表应返回 404。"""
    resp = await app_client.get("/api/admin/users/99999/credentials")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_credential_not_found(app_client, db):
    """删除不存在的凭据应返回 404。"""
    from app.models.user import User

    user = User(tg_id=555, tg_username="cred_del", role="admin")
    db.add(user)
    await db.flush()
    await db.commit()
    await db.refresh(user)

    resp = await app_client.delete(f"/api/admin/users/{user.id}/credentials/99999")
    assert resp.status_code == 404
