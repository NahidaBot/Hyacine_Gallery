"""内存向量缓存 — 维护所有 artwork embedding 的 numpy 矩阵，支持余弦相似度搜索。"""

import logging

import numpy as np
from numpy.typing import NDArray
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.artwork import ArtworkEmbedding

logger = logging.getLogger(__name__)


class VectorCache:
    def __init__(self) -> None:
        self._ids: list[int] = []
        self._matrix: NDArray[np.float32] | None = None
        # artwork_id → index 的映射
        self._id_to_idx: dict[int, int] = {}

    @property
    def size(self) -> int:
        return len(self._ids)

    async def load_from_db(self, db: AsyncSession) -> None:
        """启动时从数据库加载所有 embedding。"""
        stmt = select(ArtworkEmbedding)
        result = await db.execute(stmt)
        rows = list(result.scalars().all())

        if not rows:
            logger.info("向量缓存：数据库中无 embedding")
            return

        ids: list[int] = []
        vectors: list[NDArray[np.float32]] = []
        for row in rows:
            vec = np.frombuffer(row.embedding, dtype=np.float32)
            ids.append(row.artwork_id)
            vectors.append(vec)

        self._ids = ids
        self._matrix = np.vstack(vectors)
        self._id_to_idx = {aid: i for i, aid in enumerate(ids)}
        logger.info("向量缓存：已加载 %d 条 embedding", len(ids))

    def update(self, artwork_id: int, embedding: NDArray[np.float32]) -> None:
        """新增或更新单条 embedding。"""
        vec = embedding.reshape(1, -1).astype(np.float32)

        if artwork_id in self._id_to_idx:
            idx = self._id_to_idx[artwork_id]
            if self._matrix is not None:
                self._matrix[idx] = vec[0]
        else:
            self._ids.append(artwork_id)
            self._id_to_idx[artwork_id] = len(self._ids) - 1
            if self._matrix is None:
                self._matrix = vec
            else:
                self._matrix = np.vstack([self._matrix, vec])

    def remove(self, artwork_id: int) -> None:
        """移除单条 embedding。"""
        if artwork_id not in self._id_to_idx:
            return
        idx = self._id_to_idx[artwork_id]
        self._ids.pop(idx)
        if self._matrix is not None:
            self._matrix = np.delete(self._matrix, idx, axis=0)
            if len(self._ids) == 0:
                self._matrix = None
        # 重建索引
        self._id_to_idx = {aid: i for i, aid in enumerate(self._ids)}

    def search(
        self, query_vec: NDArray[np.float32], top_k: int = 10, threshold: float = 0.3
    ) -> list[tuple[int, float]]:
        """余弦相似度搜索，返回 (artwork_id, score) 列表。"""
        if self._matrix is None or len(self._ids) == 0:
            return []

        # 归一化查询向量
        q = query_vec.reshape(1, -1).astype(np.float32)
        q_norm = np.linalg.norm(q)
        if q_norm == 0:
            return []
        q = q / q_norm

        # 归一化矩阵（逐行）
        norms = np.linalg.norm(self._matrix, axis=1, keepdims=True)
        norms = np.maximum(norms, 1e-10)
        normed = self._matrix / norms

        # 余弦相似度 = 点积（已归一化）
        scores = (normed @ q.T).flatten()

        # 过滤低于阈值的结果
        mask = scores >= threshold
        valid_indices = np.where(mask)[0]
        if len(valid_indices) == 0:
            return []

        # 取 top_k
        top_indices = valid_indices[np.argsort(scores[valid_indices])[::-1][:top_k]]
        return [(self._ids[i], float(scores[i])) for i in top_indices]


# 全局单例
vector_cache = VectorCache()
