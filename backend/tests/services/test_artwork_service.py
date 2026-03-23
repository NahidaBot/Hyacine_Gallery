"""artwork_service 单元测试。"""

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.artwork import ArtworkImage, ArtworkSource
from app.schemas.artwork import ArtworkCreate, ArtworkUpdate
from app.services.artwork_service import (
    _hamming_distance,
    add_source,
    create_artwork,
    delete_artwork,
    delete_artwork_image,
    delete_source,
    find_similar_by_phash,
    get_artwork_by_id,
    get_artwork_by_pid,
    get_artworks,
    get_random_artwork,
    get_source_by_pid,
    merge_artworks,
    update_artwork,
)

# ── 创建 ──────────────────────────────────────────────────────────


async def test_create_artwork(db: AsyncSession):
    data = ArtworkCreate(
        platform="pixiv",
        pid="99999",
        title="Full Data",
        author="Artist",
        author_id="a001",
        source_url="https://pixiv.net/artworks/99999",
        page_count=2,
        is_nsfw=True,
        is_ai=False,
        image_urls=[
            "https://i.pximg.net/img/99999_p0.jpg",
            "https://i.pximg.net/img/99999_p1.jpg",
        ],
        tags=["landscape", "ocean"],
    )
    artwork = await create_artwork(db, data)

    assert artwork.id is not None
    assert artwork.platform == "pixiv"
    assert artwork.pid == "99999"
    assert artwork.title == "Full Data"
    assert artwork.author == "Artist"
    assert artwork.author_id == "a001"
    assert artwork.source_url == "https://pixiv.net/artworks/99999"
    assert artwork.page_count == 2
    assert artwork.is_nsfw is True
    assert artwork.is_ai is False

    assert len(artwork.images) == 2
    assert artwork.images[0].page_index == 0
    assert artwork.images[1].page_index == 1

    tag_names = {t.name for t in artwork.tags}
    assert tag_names == {"landscape", "ocean"}

    assert len(artwork.sources) == 1
    src = artwork.sources[0]
    assert src.platform == "pixiv"
    assert src.pid == "99999"
    assert src.is_primary is True


async def test_create_artwork_with_raw_info(db: AsyncSession):
    data = ArtworkCreate(platform="pixiv", pid="11111", title="Raw")
    raw = {"key": "value", "num": 42}
    artwork = await create_artwork(db, data, raw_info=raw)

    source = artwork.sources[0]
    assert source.raw_info == json.dumps(raw, ensure_ascii=False)
    parsed = json.loads(source.raw_info)
    assert parsed["key"] == "value"
    assert parsed["num"] == 42


# ── 查询 ──────────────────────────────────────────────────────────


async def test_get_artwork_by_id(db: AsyncSession, sample_artwork):
    found = await get_artwork_by_id(db, sample_artwork.id)
    assert found is not None
    assert found.id == sample_artwork.id
    assert found.title == "Test Artwork"


async def test_get_artwork_by_id_not_found(db: AsyncSession):
    assert await get_artwork_by_id(db, 999999) is None


async def test_get_artwork_by_pid(db: AsyncSession, sample_artwork):
    found = await get_artwork_by_pid(db, "pixiv", "12345")
    assert found is not None
    assert found.id == sample_artwork.id


async def test_get_artwork_by_pid_not_found(db: AsyncSession):
    assert await get_artwork_by_pid(db, "pixiv", "nonexistent") is None


async def test_get_random_artwork(db: AsyncSession, sample_artwork):
    result = await get_random_artwork(db)
    assert result is not None
    assert result.id == sample_artwork.id


async def test_get_random_artwork_empty(db: AsyncSession):
    result = await get_random_artwork(db)
    assert result is None


# ── 列表与过滤 ────────────────────────────────────────────────────


async def test_get_artworks_empty(db: AsyncSession):
    artworks, total = await get_artworks(db)
    assert artworks == []
    assert total == 0


async def test_get_artworks_paginated(db: AsyncSession):
    for i in range(3):
        await create_artwork(db, ArtworkCreate(platform="pixiv", pid=f"pg_{i}", title=f"Art {i}"))

    artworks, total = await get_artworks(db, page=1, page_size=2)
    assert total == 3
    assert len(artworks) == 2


async def test_get_artworks_filter_platform(db: AsyncSession):
    await create_artwork(db, ArtworkCreate(platform="pixiv", pid="fp_1", title="P1"))
    await create_artwork(db, ArtworkCreate(platform="twitter", pid="fp_2", title="T1"))
    await create_artwork(db, ArtworkCreate(platform="pixiv", pid="fp_3", title="P2"))

    artworks, total = await get_artworks(db, platform="pixiv")
    assert total == 2
    assert all(a.platform == "pixiv" for a in artworks)


async def test_get_artworks_filter_tag(db: AsyncSession, sample_artwork):
    artworks, total = await get_artworks(db, tag="landscape")
    assert total == 1
    assert artworks[0].id == sample_artwork.id

    artworks2, total2 = await get_artworks(db, tag="nonexistent_tag")
    assert total2 == 0


async def test_get_artworks_query_like_fallback(db: AsyncSession, sample_artwork):
    artworks, total = await get_artworks(db, q="Test")
    assert total == 1
    assert artworks[0].id == sample_artwork.id


# ── 更新 ──────────────────────────────────────────────────────────


async def test_update_artwork_fields(db: AsyncSession, sample_artwork):
    updated = await update_artwork(
        db, sample_artwork.id, ArtworkUpdate(title="New Title", is_nsfw=True)
    )
    assert updated is not None
    assert updated.title == "New Title"
    assert updated.is_nsfw is True
    # 其他字段保持不变
    assert updated.author == "Test Author"


async def test_update_artwork_tags(db: AsyncSession, sample_artwork):
    updated = await update_artwork(
        db, sample_artwork.id, ArtworkUpdate(tags=["new_tag_1", "new_tag_2"])
    )
    assert updated is not None
    tag_names = {t.name for t in updated.tags}
    assert tag_names == {"new_tag_1", "new_tag_2"}


async def test_update_artwork_not_found(db: AsyncSession):
    result = await update_artwork(db, 999999, ArtworkUpdate(title="X"))
    assert result is None


# ── 删除 ──────────────────────────────────────────────────────────


async def test_delete_artwork(db: AsyncSession, sample_artwork):
    artwork_id = sample_artwork.id
    assert await delete_artwork(db, artwork_id) is True

    # 作品本身已删除
    assert await get_artwork_by_id(db, artwork_id) is None

    # 级联：images 和 sources 也应被删除
    images = (
        (await db.execute(select(ArtworkImage).where(ArtworkImage.artwork_id == artwork_id)))
        .scalars()
        .all()
    )
    assert len(images) == 0

    sources = (
        (await db.execute(select(ArtworkSource).where(ArtworkSource.artwork_id == artwork_id)))
        .scalars()
        .all()
    )
    assert len(sources) == 0


async def test_delete_artwork_not_found(db: AsyncSession):
    assert await delete_artwork(db, 999999) is False


async def test_delete_artwork_image(db: AsyncSession):
    data = ArtworkCreate(
        platform="pixiv",
        pid="img_del",
        title="Images",
        page_count=3,
        image_urls=["url0", "url1", "url2"],
    )
    artwork = await create_artwork(db, data)
    assert len(artwork.images) == 3

    # Sort by page_index to get stable order
    sorted_images = sorted(artwork.images, key=lambda img: img.page_index)
    middle_id = sorted_images[1].id
    result = await delete_artwork_image(db, artwork.id, middle_id)
    assert result is True

    # 验证 page_count 已更新
    refreshed = await get_artwork_by_id(db, artwork.id)
    assert refreshed is not None
    assert refreshed.page_count == 2


async def test_delete_artwork_image_not_found(db: AsyncSession, sample_artwork):
    result = await delete_artwork_image(db, sample_artwork.id, 999999)
    assert result is False


# ── 来源管理 ──────────────────────────────────────────────────────


async def test_get_source_by_pid(db: AsyncSession, sample_artwork):
    source = await get_source_by_pid(db, "pixiv", "12345")
    assert source is not None
    assert source.artwork_id == sample_artwork.id
    assert source.is_primary is True


async def test_add_source(db: AsyncSession, sample_artwork):
    new_source = await add_source(
        db,
        sample_artwork.id,
        platform="twitter",
        pid="tw_001",
        source_url="https://twitter.com/status/tw_001",
    )
    assert new_source.is_primary is False
    assert new_source.platform == "twitter"
    assert new_source.artwork_id == sample_artwork.id


async def test_delete_source(db: AsyncSession, sample_artwork):
    secondary = await add_source(
        db,
        sample_artwork.id,
        platform="twitter",
        pid="tw_del",
        source_url="https://twitter.com/status/tw_del",
    )
    result = await delete_source(db, sample_artwork.id, secondary.id)
    assert result is True

    assert await get_source_by_pid(db, "twitter", "tw_del") is None


async def test_delete_source_primary_fails(db: AsyncSession, sample_artwork):
    primary = sample_artwork.sources[0]
    assert primary.is_primary is True

    result = await delete_source(db, sample_artwork.id, primary.id)
    assert result is False


# ── 合并 ──────────────────────────────────────────────────────────


async def test_merge_artworks(db: AsyncSession):
    target = await create_artwork(
        db,
        ArtworkCreate(
            platform="pixiv",
            pid="merge_target",
            title="Target",
            tags=["tag_a", "tag_b"],
            image_urls=["target_img"],
        ),
    )
    source = await create_artwork(
        db,
        ArtworkCreate(
            platform="twitter",
            pid="merge_source",
            title="Source",
            tags=["tag_b", "tag_c"],
            image_urls=["source_img"],
        ),
    )
    source_id = source.id

    merged = await merge_artworks(db, target.id, source.id)
    assert merged is not None
    assert merged.id == target.id

    # 标签取并集：target 有 tag_a/tag_b，source 有 tag_b/tag_c，合并后应有三个
    tag_names = {t.name for t in merged.tags}
    assert "tag_a" in tag_names
    assert "tag_b" in tag_names
    assert "tag_c" in tag_names

    # 来源已迁移（至少包含 target 原来的 pixiv 来源）
    assert len(merged.sources) >= 1
    assert "pixiv" in {s.platform for s in merged.sources}

    # 源作品已删除
    assert await get_artwork_by_id(db, source_id) is None


async def test_merge_artworks_not_found(db: AsyncSession, sample_artwork):
    assert await merge_artworks(db, sample_artwork.id, 999999) is None
    assert await merge_artworks(db, 999999, sample_artwork.id) is None


# ── pHash 相似度 ──────────────────────────────────────────────────


async def test_hamming_distance():
    assert _hamming_distance("0000000000000000", "0000000000000000") == 0
    assert _hamming_distance("ffffffffffffffff", "0000000000000000") == 64
    assert _hamming_distance("ff00000000000000", "fe00000000000000") == 1


async def test_find_similar_by_phash(db: AsyncSession):
    a1 = await create_artwork(
        db,
        ArtworkCreate(platform="pixiv", pid="ph_1", image_urls=["img1"]),
    )
    a2 = await create_artwork(
        db,
        ArtworkCreate(platform="pixiv", pid="ph_2", image_urls=["img2"]),
    )

    # 设置已知 phash
    a1.images[0].phash = "abcdef1234567890"
    a2.images[0].phash = "abcdef1234567891"  # 汉明距离 = 1
    await db.commit()

    results = await find_similar_by_phash(db, "abcdef1234567890", threshold=8)
    assert len(results) >= 2
    # 第一个应该是精确匹配（距离 0）
    assert results[0][1] == 0
    # 第二个距离 1
    assert results[1][1] == 1


async def test_find_similar_by_phash_empty(db: AsyncSession):
    results = await find_similar_by_phash(db, "", threshold=8)
    assert results == []


async def test_find_similar_by_phash_no_match(db: AsyncSession):
    artwork = await create_artwork(
        db,
        ArtworkCreate(platform="pixiv", pid="ph_no", image_urls=["img"]),
    )
    artwork.images[0].phash = "ffffffffffffffff"
    await db.commit()

    # 搜索与之完全不同的 hash，阈值设为 0
    results = await find_similar_by_phash(db, "0000000000000000", threshold=0)
    assert results == []
