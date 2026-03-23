"""fts_service 单元测试。"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.artwork import ArtworkCreate
from app.services.artwork_service import create_artwork
from app.services.fts_service import ensure_fts_index, fts_search_artwork_ids, rebuild_fts_index


async def test_ensure_fts_index(db: AsyncSession):
    """ensure_fts_index 应无异常创建 FTS5 虚拟表。"""
    await ensure_fts_index(db)


async def test_rebuild_fts_index(db: AsyncSession, sample_artwork):
    """rebuild 应返回索引的文档数量。"""
    await ensure_fts_index(db)
    count = await rebuild_fts_index(db)
    assert count >= 1


async def test_fts_search_match(db: AsyncSession):
    """搜索应能匹配标题中的关键词。"""
    await ensure_fts_index(db)
    artwork = await create_artwork(
        db,
        ArtworkCreate(
            platform="pixiv",
            pid="fts1",
            title="Beautiful Sunset",
            image_urls=["https://example.com/1.jpg"],
        ),
    )
    # 手动插入 FTS 记录（避免 rebuild 中的 DELETE 触发 greenlet 问题）
    from sqlalchemy import text

    await db.execute(
        text(
            "INSERT INTO artworks_fts(rowid, title, title_zh, author) VALUES (:id, :title, '', '')"
        ),
        {"id": artwork.id, "title": artwork.title},
    )
    await db.commit()

    ids = await fts_search_artwork_ids(db, "sunset")
    assert artwork.id in ids


async def test_fts_search_no_match(db: AsyncSession):
    """搜索不存在的词应返回空列表。"""
    await ensure_fts_index(db)
    await rebuild_fts_index(db)
    ids = await fts_search_artwork_ids(db, "xyznonexistent")
    assert ids == []


async def test_fts_search_empty_query(db: AsyncSession):
    """空查询应返回空列表。"""
    await ensure_fts_index(db)
    ids = await fts_search_artwork_ids(db, "")
    assert ids == []


async def test_fts_search_failure_returns_empty(db: AsyncSession):
    """FTS 查询异常时应返回空列表（fallback）。"""
    # 不调用 ensure_fts_index，直接搜索 — FTS 表不存在，应返回 []
    ids = await fts_search_artwork_ids(db, "test")
    assert ids == []
