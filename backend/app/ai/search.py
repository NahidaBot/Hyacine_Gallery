"""语义搜索服务 — 基于 embedding 的自然语言搜索。"""

import hashlib
import logging

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.factory import get_embedding_provider
from app.ai.vector_cache import vector_cache
from app.models.artwork import Artwork, ArtworkEmbedding

logger = logging.getLogger(__name__)


def build_embedding_text(artwork: Artwork) -> str:
    """构造用于 embedding 的文本，包含标题、中文标题、作者和标签。"""
    parts = []
    if artwork.title:
        parts.append(artwork.title)
    if artwork.title_zh:
        parts.append(artwork.title_zh)
    if artwork.author:
        parts.append(artwork.author)
    tag_names = [t.name for t in artwork.tags]
    if tag_names:
        parts.append(" ".join(tag_names))
    return " | ".join(parts)


def _text_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


async def compute_and_store_embedding(db: AsyncSession, artwork: Artwork) -> bool:
    """计算单个作品的 embedding 并存入数据库 + 缓存。返回是否成功。"""
    provider = get_embedding_provider()
    if provider is None:
        return False

    text = build_embedding_text(artwork)
    if not text.strip():
        return False

    th = _text_hash(text)

    # 检查是否已有相同 hash 的 embedding（无需重算）
    existing = await db.get(ArtworkEmbedding, artwork.id)
    if existing and existing.text_hash == th:
        return True

    try:
        vectors = await provider.embed([text])
        vec = np.array(vectors[0], dtype=np.float32)
    except Exception:
        logger.warning("Embedding 计算失败: artwork_id=%d", artwork.id, exc_info=True)
        return False

    embedding_bytes = vec.tobytes()

    if existing:
        existing.embedding = embedding_bytes
        existing.text_hash = th
    else:
        db.add(
            ArtworkEmbedding(
                artwork_id=artwork.id,
                text_hash=th,
                embedding=embedding_bytes,
            )
        )
    await db.flush()

    # 更新内存缓存
    vector_cache.update(artwork.id, vec)
    return True


async def semantic_search(
    db: AsyncSession, query: str, top_k: int = 10, threshold: float = 0.3
) -> list[tuple[int, float]]:
    """语义搜索，返回 (artwork_id, score) 列表。"""
    provider = get_embedding_provider()
    if provider is None:
        return []

    try:
        vectors = await provider.embed([query])
        query_vec = np.array(vectors[0], dtype=np.float32)
    except Exception:
        logger.warning("查询 embedding 计算失败: %s", query, exc_info=True)
        return []

    return vector_cache.search(query_vec, top_k=top_k, threshold=threshold)


async def remove_embedding(db: AsyncSession, artwork_id: int) -> None:
    """删除作品的 embedding（数据库 + 缓存）。"""
    existing = await db.get(ArtworkEmbedding, artwork_id)
    if existing:
        await db.delete(existing)
        await db.flush()
    vector_cache.remove(artwork_id)
