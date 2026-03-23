"""测试管理后台 API 路由。"""

from unittest.mock import AsyncMock, patch

import pytest

from app.crawlers.base import CrawlResult


@pytest.mark.asyncio
async def test_create_artwork(app_client):
    """POST /api/admin/artworks 应创建作品。"""
    resp = await app_client.post(
        "/api/admin/artworks",
        json={
            "platform": "pixiv",
            "pid": "11111",
            "title": "New Artwork",
            "author": "Artist",
            "source_url": "https://pixiv.net/artworks/11111",
            "tags": ["test"],
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["platform"] == "pixiv"
    assert body["pid"] == "11111"
    assert body["title"] == "New Artwork"


@pytest.mark.asyncio
async def test_update_artwork(app_client, sample_artwork):
    """PUT /api/admin/artworks/{id} 应更新作品。"""
    resp = await app_client.put(
        f"/api/admin/artworks/{sample_artwork.id}",
        json={"title": "Updated Title"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated Title"


@pytest.mark.asyncio
async def test_update_artwork_not_found(app_client):
    """更新不存在的作品应返回 404。"""
    resp = await app_client.put(
        "/api/admin/artworks/99999",
        json={"title": "X"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_artwork(app_client, sample_artwork):
    """DELETE /api/admin/artworks/{id} 应删除作品。"""
    resp = await app_client.delete(f"/api/admin/artworks/{sample_artwork.id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "deleted"

    # 确认已删除
    resp2 = await app_client.get(f"/api/artworks/{sample_artwork.id}")
    assert resp2.status_code == 404


@pytest.mark.asyncio
async def test_delete_artwork_not_found(app_client):
    """删除不存在的作品应返回 404。"""
    resp = await app_client.delete("/api/admin/artworks/99999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_tag(app_client):
    """POST /api/admin/tags 应创建标签。"""
    resp = await app_client.post(
        "/api/admin/tags",
        json={"name": "new_tag", "type": "general"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "new_tag"
    assert body["type"] == "general"


@pytest.mark.asyncio
async def test_update_tag(app_client, sample_tag):
    """PUT /api/admin/tags/{id} 应更新标签。"""
    resp = await app_client.put(
        f"/api/admin/tags/{sample_tag.id}",
        json={"name": "renamed_tag"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "renamed_tag"


@pytest.mark.asyncio
async def test_delete_tag(app_client, sample_tag):
    """DELETE /api/admin/tags/{id} 应删除标签。"""
    resp = await app_client.delete(f"/api/admin/tags/{sample_tag.id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "deleted"


@pytest.mark.asyncio
async def test_create_tag_type(app_client):
    """POST /api/admin/tag-types 应创建标签类型。"""
    resp = await app_client.post(
        "/api/admin/tag-types",
        json={"name": "custom_type", "label": "自定义", "color": "#ff0000"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "custom_type"
    assert body["label"] == "自定义"


@pytest.mark.asyncio
async def test_update_tag_type(app_client):
    """PUT /api/admin/tag-types/{id} 应更新标签类型。"""
    # 先创建
    create_resp = await app_client.post(
        "/api/admin/tag-types",
        json={"name": "to_update", "label": "原标签"},
    )
    tt_id = create_resp.json()["id"]

    resp = await app_client.put(
        f"/api/admin/tag-types/{tt_id}",
        json={"label": "更新后标签"},
    )
    assert resp.status_code == 200
    assert resp.json()["label"] == "更新后标签"


@pytest.mark.asyncio
async def test_delete_tag_type(app_client):
    """DELETE /api/admin/tag-types/{id} 应删除标签类型。"""
    create_resp = await app_client.post(
        "/api/admin/tag-types",
        json={"name": "to_delete", "label": "待删除"},
    )
    tt_id = create_resp.json()["id"]

    resp = await app_client.delete(f"/api/admin/tag-types/{tt_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "deleted"


@pytest.mark.asyncio
async def test_get_duplicate_tags(app_client):
    """GET /api/admin/tags/duplicates 应返回重复标签列表。"""
    resp = await app_client.get("/api/admin/tags/duplicates")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_merge_tags(app_client, db):
    """POST /api/admin/tags/merge 应合并标签。"""
    from app.schemas.tag import TagCreate
    from app.services.tag_service import create_tag

    tag_a = await create_tag(db, TagCreate(name="tag_keep", type="general"))
    tag_b = await create_tag(db, TagCreate(name="tag_merge", type="general"))

    resp = await app_client.post(
        "/api/admin/tags/merge",
        json={"keep_id": tag_a.id, "merge_id": tag_b.id},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "merged"


@pytest.mark.asyncio
async def test_import_artwork(app_client):
    """POST /api/admin/artworks/import 应通过 URL 导入作品。"""
    mock_result = CrawlResult(
        success=True,
        platform="pixiv",
        pid="99999",
        title="Imported Artwork",
        author="Imported Author",
        author_id="author_099",
        source_url="https://pixiv.net/artworks/99999",
        image_urls=["https://i.pximg.net/img/99999_p0.jpg"],
        tags=["imported"],
    )
    with (
        patch("app.api.admin.crawl", new_callable=AsyncMock, return_value=mock_result),
        patch("app.api.admin.try_extract_identity", return_value=None),
        patch(
            "app.services.storage_service.download_and_store_images",
            new_callable=AsyncMock,
        ),
    ):
        resp = await app_client.post(
            "/api/admin/artworks/import",
            json={"url": "https://pixiv.net/artworks/99999"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["artwork"] is not None
    assert body["artwork"]["pid"] == "99999"


@pytest.mark.asyncio
async def test_import_artwork_existing(app_client, sample_artwork):
    """已存在的 pid 应返回已有作品而非重新创建。"""
    # try_extract_identity 匹配 -> 命中缓存
    with patch(
        "app.api.admin.try_extract_identity",
        return_value=("pixiv", "12345"),
    ):
        resp = await app_client.post(
            "/api/admin/artworks/import",
            json={"url": "https://pixiv.net/artworks/12345"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["artwork"]["id"] == sample_artwork.id
    assert "已存在" in body["message"]


@pytest.mark.asyncio
async def test_delete_artwork_image(app_client, sample_artwork):
    """DELETE /api/admin/artworks/{id}/images/{img_id} 应删除图片。"""
    # sample_artwork 有 1 张图片
    img_id = sample_artwork.images[0].id
    resp = await app_client.delete(f"/api/admin/artworks/{sample_artwork.id}/images/{img_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "deleted"


@pytest.mark.asyncio
async def test_merge_artwork(app_client, db):
    """POST /api/admin/artworks/{id}/merge 应合并两个作品。"""
    from app.schemas.artwork import ArtworkCreate
    from app.services.artwork_service import create_artwork

    art_a = await create_artwork(
        db,
        ArtworkCreate(
            platform="pixiv",
            pid="merge_a",
            title="A",
            image_urls=["https://example.com/a.jpg"],
            tags=["tag_a"],
        ),
    )
    art_b = await create_artwork(
        db,
        ArtworkCreate(
            platform="twitter",
            pid="merge_b",
            title="B",
            image_urls=["https://example.com/b.jpg"],
            tags=["tag_b"],
        ),
    )

    resp = await app_client.post(
        f"/api/admin/artworks/{art_a.id}/merge",
        json={"source_artwork_id": art_b.id},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == art_a.id


@pytest.mark.asyncio
async def test_fts_rebuild(app_client):
    """POST /api/admin/fts/rebuild 应重建 FTS 索引。"""
    resp = await app_client.post("/api/admin/fts/rebuild")
    assert resp.status_code == 200
    body = resp.json()
    assert "indexed" in body


@pytest.mark.asyncio
async def test_delete_source(app_client, db):
    """DELETE /api/admin/artworks/{id}/sources/{sid} 应删除非主要来源。"""
    from app.schemas.artwork import ArtworkCreate
    from app.services.artwork_service import add_source, create_artwork

    art = await create_artwork(
        db,
        ArtworkCreate(
            platform="pixiv",
            pid="src_del",
            title="Source Del",
            image_urls=["https://example.com/s.jpg"],
            tags=[],
        ),
    )
    # 添加一个非主要来源
    source = await add_source(db, art.id, "twitter", "tw_del", "https://twitter.com/tw_del")
    resp = await app_client.delete(f"/api/admin/artworks/{art.id}/sources/{source.id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "deleted"


@pytest.mark.asyncio
async def test_delete_source_not_found(app_client, sample_artwork):
    """删除不存在的来源应返回 404。"""
    resp = await app_client.delete(f"/api/admin/artworks/{sample_artwork.id}/sources/99999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_orphan_images(app_client):
    """GET /api/admin/cleanup/orphan-images 应返回列表。"""
    resp = await app_client.get("/api/admin/cleanup/orphan-images")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_cleanup_orphan_images(app_client):
    """POST /api/admin/cleanup/orphan-images 应返回 cleaned 数量。"""
    resp = await app_client.post("/api/admin/cleanup/orphan-images")
    assert resp.status_code == 200
    body = resp.json()
    assert "cleaned" in body
    assert body["cleaned"] >= 0


@pytest.mark.asyncio
async def test_list_tag_types(app_client):
    """GET /api/admin/tag-types 应返回标签类型列表。"""
    resp = await app_client.get("/api/admin/tag-types")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    # 默认 seed 会创建一些类型
    assert len(body) > 0


@pytest.mark.asyncio
async def test_update_author_not_found(app_client):
    """更新不存在的作者应返回 404。"""
    resp = await app_client.put(
        "/api/admin/authors/99999",
        json={"name": "X"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_author_not_found(app_client):
    """删除不存在的作者应返回 404。"""
    resp = await app_client.delete("/api/admin/authors/99999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_tag_not_found(app_client):
    """更新不存在的标签应返回 404。"""
    resp = await app_client.put(
        "/api/admin/tags/99999",
        json={"name": "x"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_tag_not_found(app_client):
    """删除不存在的标签应返回 404。"""
    resp = await app_client.delete("/api/admin/tags/99999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_tag_type_not_found(app_client):
    """更新不存在的标签类型应返回 404。"""
    resp = await app_client.put(
        "/api/admin/tag-types/99999",
        json={"label": "X"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_tag_type_not_found(app_client):
    """删除不存在的标签类型应返回 404。"""
    resp = await app_client.delete("/api/admin/tag-types/99999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_merge_artwork_self(app_client, sample_artwork):
    """不能将作品合并到自身，应返回 400。"""
    resp = await app_client.post(
        f"/api/admin/artworks/{sample_artwork.id}/merge",
        json={"source_artwork_id": sample_artwork.id},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_merge_tags_missing_params(app_client):
    """合并标签缺少参数应返回 400。"""
    resp = await app_client.post("/api/admin/tags/merge", json={})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_import_crawl_failure(app_client):
    """抓取失败应返回 422。"""
    fail_result = CrawlResult(success=False, error="网络错误")
    with (
        patch("app.api.admin.crawl", new_callable=AsyncMock, return_value=fail_result),
        patch("app.api.admin.try_extract_identity", return_value=None),
    ):
        resp = await app_client.post(
            "/api/admin/artworks/import",
            json={"url": "https://example.com/fail"},
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_delete_artwork_image_not_found(app_client, sample_artwork):
    """删除不存在的图片应返回 404。"""
    resp = await app_client.delete(f"/api/admin/artworks/{sample_artwork.id}/images/99999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_author(app_client):
    """POST /api/admin/authors 应创建作者。"""
    resp = await app_client.post(
        "/api/admin/authors",
        json={"name": "New Author", "platform": "pixiv", "platform_uid": "uid_new"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "New Author"
    assert body["platform"] == "pixiv"


@pytest.mark.asyncio
async def test_update_author(app_client, sample_author):
    """PUT /api/admin/authors/{id} 应更新作者。"""
    resp = await app_client.put(
        f"/api/admin/authors/{sample_author.id}",
        json={"name": "Renamed Author"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Renamed Author"


@pytest.mark.asyncio
async def test_delete_author(app_client, sample_author):
    """DELETE /api/admin/authors/{id} 应删除作者。"""
    resp = await app_client.delete(f"/api/admin/authors/{sample_author.id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "deleted"
