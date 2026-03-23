"""测试友情链接 API 路由。"""

import pytest


@pytest.mark.asyncio
async def test_list_links_public(app_client):
    """GET /api/links 公开接口应仅返回已启用的链接。"""
    # 先通过管理接口创建两个链接，一个启用一个禁用
    await app_client.post(
        "/api/admin/links",
        json={"name": "Enabled Link", "url": "https://enabled.example.com", "enabled": True},
    )
    await app_client.post(
        "/api/admin/links",
        json={"name": "Disabled Link", "url": "https://disabled.example.com", "enabled": False},
    )

    resp = await app_client.get("/api/links")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    # 公开接口仅返回 enabled=True 的
    for link in body:
        assert link["enabled"] is True
    names = [lk["name"] for lk in body]
    assert "Enabled Link" in names
    assert "Disabled Link" not in names


@pytest.mark.asyncio
async def test_admin_create_link(app_client):
    """POST /api/admin/links 应创建友情链接。"""
    resp = await app_client.post(
        "/api/admin/links",
        json={
            "name": "Test Link",
            "url": "https://test.example.com",
            "description": "测试链接",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Test Link"
    assert body["url"] == "https://test.example.com"


@pytest.mark.asyncio
async def test_admin_list_links(app_client):
    """GET /api/admin/links 应返回所有链接（含禁用）。"""
    # 创建一个禁用链接
    await app_client.post(
        "/api/admin/links",
        json={"name": "Admin Link", "url": "https://admin.example.com", "enabled": False},
    )

    resp = await app_client.get("/api/admin/links")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) >= 1


@pytest.mark.asyncio
async def test_admin_update_link(app_client):
    """PUT /api/admin/links/{id} 应更新友情链接。"""
    create_resp = await app_client.post(
        "/api/admin/links",
        json={"name": "To Update", "url": "https://update.example.com"},
    )
    link_id = create_resp.json()["id"]

    resp = await app_client.put(
        f"/api/admin/links/{link_id}",
        json={"name": "Updated Link"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Link"


@pytest.mark.asyncio
async def test_admin_delete_link(app_client):
    """DELETE /api/admin/links/{id} 应删除友情链接。"""
    create_resp = await app_client.post(
        "/api/admin/links",
        json={"name": "To Delete", "url": "https://delete.example.com"},
    )
    link_id = create_resp.json()["id"]

    resp = await app_client.delete(f"/api/admin/links/{link_id}")
    assert resp.status_code == 200
