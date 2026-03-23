"""测试公开标签 API 路由。"""

import pytest


@pytest.mark.asyncio
async def test_list_tags(app_client, sample_artwork):
    """GET /api/tags 应返回标签列表。"""
    resp = await app_client.get("/api/tags")
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert "total" in body
    assert body["total"] >= 1


@pytest.mark.asyncio
async def test_list_tags_filter_type(app_client, sample_artwork):
    """按 type 过滤标签。"""
    resp = await app_client.get("/api/tags", params={"type": "general"})
    assert resp.status_code == 200
    body = resp.json()
    for tag in body["data"]:
        assert tag["type"] == "general"


@pytest.mark.asyncio
async def test_list_tag_types(app_client):
    """GET /api/tags/types 应返回标签类型列表。"""
    resp = await app_client.get("/api/tags/types")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    # seed_default_tag_types 至少会创建一些默认类型
    assert len(body) >= 1
    assert "name" in body[0]


@pytest.mark.asyncio
async def test_get_tag(app_client, sample_artwork):
    """GET /api/tags/{name} 应返回指定标签。"""
    resp = await app_client.get("/api/tags/landscape")
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "landscape"
    assert "artwork_count" in body


@pytest.mark.asyncio
async def test_get_tag_not_found(app_client):
    """不存在的标签应返回 404。"""
    resp = await app_client.get("/api/tags/nonexistent_tag_xyz")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_tag_artworks(app_client, sample_artwork):
    """GET /api/tags/{name}/artworks 应返回该标签下的作品。"""
    resp = await app_client.get("/api/tags/landscape/artworks")
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert "total" in body
    assert body["total"] >= 1
