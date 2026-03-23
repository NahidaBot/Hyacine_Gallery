"""测试公开作品 API 路由。"""

import pytest


@pytest.mark.asyncio
async def test_list_artworks(app_client, sample_artwork):
    """GET /api/artworks 应返回分页列表。"""
    resp = await app_client.get("/api/artworks")
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert "total" in body
    assert body["total"] >= 1
    assert len(body["data"]) >= 1
    assert body["data"][0]["platform"] == "pixiv"


@pytest.mark.asyncio
async def test_list_artworks_empty(app_client):
    """无作品时应返回空列表。"""
    resp = await app_client.get("/api/artworks")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"] == []
    assert body["total"] == 0


@pytest.mark.asyncio
async def test_list_artworks_filter_platform(app_client, sample_artwork):
    """按 platform 过滤应仅返回匹配的作品。"""
    resp = await app_client.get("/api/artworks", params={"platform": "pixiv"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    for item in body["data"]:
        assert item["platform"] == "pixiv"

    # 不存在的 platform 应返回空
    resp2 = await app_client.get("/api/artworks", params={"platform": "nonexistent"})
    assert resp2.status_code == 200
    assert resp2.json()["total"] == 0


@pytest.mark.asyncio
async def test_list_artworks_filter_tag(app_client, sample_artwork):
    """按 tag 过滤应仅返回含该标签的作品。"""
    resp = await app_client.get("/api/artworks", params={"tag": "landscape"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1


@pytest.mark.asyncio
async def test_get_artwork(app_client, sample_artwork):
    """GET /api/artworks/{id} 应返回作品详情。"""
    resp = await app_client.get(f"/api/artworks/{sample_artwork.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == sample_artwork.id
    assert body["platform"] == "pixiv"
    assert "images" in body
    assert "tags" in body


@pytest.mark.asyncio
async def test_get_artwork_not_found(app_client):
    """不存在的作品应返回 404。"""
    resp = await app_client.get("/api/artworks/99999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_random_artwork(app_client, sample_artwork):
    """GET /api/artworks/random 应返回一个随机作品。"""
    resp = await app_client.get("/api/artworks/random")
    assert resp.status_code == 200
    body = resp.json()
    assert "id" in body
    assert "platform" in body


@pytest.mark.asyncio
async def test_random_artwork_empty(app_client):
    """无作品时 random 应返回 404。"""
    resp = await app_client.get("/api/artworks/random")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_search_artworks_fallback(app_client, sample_artwork):
    """GET /api/artworks/search 未启用 embedding 时应 fallback 到关键词搜索。"""
    resp = await app_client.get("/api/artworks/search", params={"q": "Test"})
    assert resp.status_code == 200
    body = resp.json()
    assert "results" in body
    assert "query" in body
    assert body["query"] == "Test"
    # fallback 模式下 score 都是 1.0
    for result in body["results"]:
        assert result["score"] == 1.0
        assert "artwork" in result


@pytest.mark.asyncio
async def test_search_artworks_empty_query(app_client):
    """搜索空数据库应返回空结果。"""
    resp = await app_client.get("/api/artworks/search", params={"q": "nonexistent"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["results"] == []


@pytest.mark.asyncio
async def test_list_artworks_pagination(app_client, db):
    """测试分页参数。"""
    from app.schemas.artwork import ArtworkCreate
    from app.services.artwork_service import create_artwork

    for i in range(5):
        await create_artwork(
            db,
            ArtworkCreate(
                platform="pixiv",
                pid=f"page_{i}",
                title=f"Page {i}",
                image_urls=[f"https://example.com/{i}.jpg"],
                tags=[],
            ),
        )

    resp = await app_client.get("/api/artworks", params={"page": 1, "page_size": 2})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data"]) == 2
    assert body["total"] == 5
    assert body["page"] == 1
    assert body["page_size"] == 2

    # 第二页
    resp2 = await app_client.get("/api/artworks", params={"page": 2, "page_size": 2})
    assert resp2.status_code == 200
    body2 = resp2.json()
    assert len(body2["data"]) == 2


@pytest.mark.asyncio
async def test_list_artworks_search_q(app_client, sample_artwork):
    """按关键词 q 搜索。"""
    resp = await app_client.get("/api/artworks", params={"q": "Test Artwork"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
