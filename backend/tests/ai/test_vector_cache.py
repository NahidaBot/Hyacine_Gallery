"""VectorCache 单元测试。"""

import numpy as np

from app.ai.vector_cache import VectorCache


class TestVectorCache:
    def test_update_and_search(self):
        """添加 3 个 embedding，搜索与其中一个相似的向量。"""
        cache = VectorCache()
        cache.update(1, np.array([1.0, 0.0, 0.0], dtype=np.float32))
        cache.update(2, np.array([0.0, 1.0, 0.0], dtype=np.float32))
        cache.update(3, np.array([0.0, 0.0, 1.0], dtype=np.float32))

        assert cache.size == 3

        # 查询与 artwork 1 最相似的向量
        results = cache.search(np.array([0.9, 0.1, 0.0], dtype=np.float32), top_k=3, threshold=0.3)
        assert len(results) > 0
        # 最高分应该是 artwork_id=1
        assert results[0][0] == 1
        assert results[0][1] > 0.9

    def test_update_existing(self):
        """更新已有 artwork_id，size 不应增加。"""
        cache = VectorCache()
        cache.update(1, np.array([1.0, 0.0, 0.0], dtype=np.float32))
        assert cache.size == 1

        cache.update(1, np.array([0.0, 1.0, 0.0], dtype=np.float32))
        assert cache.size == 1

        # 搜索应返回更新后的向量
        results = cache.search(np.array([0.0, 1.0, 0.0], dtype=np.float32), top_k=1, threshold=0.3)
        assert len(results) == 1
        assert results[0][0] == 1
        assert results[0][1] > 0.99

    def test_remove(self):
        """添加后移除，size 应减少。"""
        cache = VectorCache()
        cache.update(1, np.array([1.0, 0.0, 0.0], dtype=np.float32))
        cache.update(2, np.array([0.0, 1.0, 0.0], dtype=np.float32))
        assert cache.size == 2

        cache.remove(1)
        assert cache.size == 1

        # 搜索不应返回已移除的 artwork
        results = cache.search(np.array([1.0, 0.0, 0.0], dtype=np.float32), top_k=10, threshold=0.0)
        artwork_ids = [r[0] for r in results]
        assert 1 not in artwork_ids

    def test_search_empty(self):
        """空缓存搜索返回空列表。"""
        cache = VectorCache()
        results = cache.search(np.array([1.0, 0.0, 0.0], dtype=np.float32))
        assert results == []

    def test_search_threshold(self):
        """低于阈值的结果应被排除。"""
        cache = VectorCache()
        cache.update(1, np.array([1.0, 0.0, 0.0], dtype=np.float32))
        cache.update(2, np.array([0.0, 1.0, 0.0], dtype=np.float32))

        # 搜索 [1, 0, 0]，高阈值应只返回 artwork 1
        results = cache.search(np.array([1.0, 0.0, 0.0], dtype=np.float32), threshold=0.9)
        assert len(results) == 1
        assert results[0][0] == 1

    def test_search_zero_norm(self):
        """零向量查询返回空列表。"""
        cache = VectorCache()
        cache.update(1, np.array([1.0, 0.0, 0.0], dtype=np.float32))

        results = cache.search(np.array([0.0, 0.0, 0.0], dtype=np.float32))
        assert results == []
