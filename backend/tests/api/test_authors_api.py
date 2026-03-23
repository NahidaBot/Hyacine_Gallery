"""测试公开作者 API 路由。"""

import pytest


@pytest.mark.asyncio
async def test_list_authors(app_client, sample_author):
    """GET /api/authors 应返回作者列表。"""
    resp = await app_client.get("/api/authors")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) >= 1
    assert body[0]["name"] == "Pixiv Artist"


@pytest.mark.asyncio
async def test_get_author(app_client, sample_author):
    """GET /api/authors/{id} 应返回作者详情。"""
    resp = await app_client.get(f"/api/authors/{sample_author.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == sample_author.id
    assert body["name"] == "Pixiv Artist"


@pytest.mark.asyncio
async def test_get_author_not_found(app_client):
    """不存在的作者应返回 404。"""
    resp = await app_client.get("/api/authors/99999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_author_by_name(app_client, sample_author):
    """GET /api/authors/by-name/{name} 应按名称查找作者。"""
    resp = await app_client.get(f"/api/authors/by-name/{sample_author.name}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == sample_author.name


@pytest.mark.asyncio
async def test_get_author_artworks(app_client, sample_author):
    """GET /api/authors/{id}/artworks 应返回该作者的作品列表。"""
    resp = await app_client.get(f"/api/authors/{sample_author.id}/artworks")
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert "total" in body


@pytest.mark.asyncio
async def test_get_author_by_name_not_found(app_client):
    """按名称查找不存在的作者应返回 404。"""
    resp = await app_client.get("/api/authors/by-name/NonExistentArtist")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_author_artworks_not_found(app_client):
    """不存在的作者的作品列表应返回 404。"""
    resp = await app_client.get("/api/authors/99999/artworks")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_authors_empty(app_client):
    """无作者时应返回空列表。"""
    resp = await app_client.get("/api/authors")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) == 0


@pytest.mark.asyncio
async def test_list_authors_filter_platform(app_client, sample_author):
    """按 platform 过滤作者。"""
    resp = await app_client.get("/api/authors", params={"platform": "pixiv"})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) >= 1
    for a in body:
        assert a["platform"] == "pixiv"

    # 不存在的 platform 应返回空
    resp2 = await app_client.get("/api/authors", params={"platform": "nonexistent"})
    assert resp2.status_code == 200
    assert len(resp2.json()) == 0
