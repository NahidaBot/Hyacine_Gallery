"""全文搜索服务 — SQLite FTS5 / PostgreSQL pg_trgm 双模式。"""

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import engine

logger = logging.getLogger(__name__)

_is_sqlite = str(engine.url).startswith("sqlite")


async def ensure_fts_index(db: AsyncSession) -> None:
    """确保 FTS 索引/虚拟表已创建。在应用启动时调用。"""
    if _is_sqlite:
        await db.execute(
            text(
                "CREATE VIRTUAL TABLE IF NOT EXISTS artworks_fts "
                "USING fts5(title, title_zh, author, "
                "content='artworks', content_rowid='id', tokenize='trigram')"
            )
        )
        await db.commit()
    else:
        # PostgreSQL: pg_trgm 扩展 + GIN 索引支持中文子串搜索
        await db.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        await db.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_artworks_trgm "
                "ON artworks USING GIN ("
                "(coalesce(title, '') || ' ' || coalesce(title_zh, '') "
                "|| ' ' || coalesce(author, '')) gin_trgm_ops)"
            )
        )
        await db.commit()
    logger.info("FTS 索引已就绪 (sqlite=%s)", _is_sqlite)


async def fts_search_artwork_ids(db: AsyncSession, query: str, limit: int = 100) -> list[int]:
    """通过 FTS 搜索作品，返回匹配的 artwork_id 列表。"""
    if not query.strip():
        return []

    if _is_sqlite:
        result = await db.execute(
            text(
                "SELECT rowid FROM artworks_fts "
                "WHERE artworks_fts MATCH :q ORDER BY rank LIMIT :limit"
            ),
            {"q": query, "limit": limit},
        )
        return [row[0] for row in result.all()]
    else:
        # PostgreSQL: trigram 相似度搜索
        result = await db.execute(
            text(
                "SELECT id FROM artworks "
                "WHERE (coalesce(title, '') || ' ' || coalesce(title_zh, '') "
                "|| ' ' || coalesce(author, '')) %% :q "
                "ORDER BY similarity("
                "coalesce(title, '') || ' ' || coalesce(title_zh, '') "
                "|| ' ' || coalesce(author, ''), :q) DESC "
                "LIMIT :limit"
            ),
            {"q": query, "limit": limit},
        )
        return [row[0] for row in result.all()]


async def rebuild_fts_index(db: AsyncSession) -> int:
    """重建 FTS 索引（仅 SQLite）。返回索引的文档数。"""
    if not _is_sqlite:
        return 0

    await db.execute(text("DELETE FROM artworks_fts"))
    await db.execute(
        text(
            "INSERT INTO artworks_fts(rowid, title, title_zh, author) "
            "SELECT id, coalesce(title, ''), coalesce(title_zh, ''), "
            "coalesce(author, '') FROM artworks"
        )
    )
    await db.commit()

    result = await db.execute(text("SELECT COUNT(*) FROM artworks_fts"))
    count: int = result.scalar_one()
    logger.info("FTS 索引已重建: %d 条文档", count)
    return count
