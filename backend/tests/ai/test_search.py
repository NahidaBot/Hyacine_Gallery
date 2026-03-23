"""语义搜索服务单元测试。"""

from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.search import (
    build_embedding_text,
    compute_and_store_embedding,
    remove_embedding,
    semantic_search,
)
from app.models.artwork import Artwork, ArtworkEmbedding
from app.schemas.artwork import ArtworkCreate


def _make_artwork(
    *,
    title: str = "Test",
    title_zh: str = "",
    author: str = "Artist",
    tags: list | None = None,
) -> Artwork:
    """创建一个用于测试的 Artwork mock 对象。"""
    artwork = MagicMock(spec=Artwork)
    artwork.title = title
    artwork.title_zh = title_zh
    artwork.author = author
    # tags 是包含 .name 属性的对象列表
    if tags is None:
        tags = []
    tag_objs = []
    for t in tags:
        tag = MagicMock()
        tag.name = t
        tag_objs.append(tag)
    artwork.tags = tag_objs
    return artwork


class TestBuildEmbeddingText:
    def test_build_embedding_text(self):
        """应将标题、中文标题、作者和标签组合成文本。"""
        artwork = _make_artwork(
            title="Sunset",
            title_zh="日落",
            author="Monet",
            tags=["landscape", "nature"],
        )
        text = build_embedding_text(artwork)
        assert "Sunset" in text
        assert "日落" in text
        assert "Monet" in text
        assert "landscape" in text
        assert "nature" in text
        # 使用 " | " 分隔
        assert " | " in text

    def test_build_embedding_text_empty(self):
        """字段为空时不应包含空段。"""
        artwork = _make_artwork(title="", title_zh="", author="", tags=[])
        text = build_embedding_text(artwork)
        assert text == ""


class TestComputeAndStoreEmbedding:
    async def test_compute_and_store_embedding(self, db: AsyncSession):
        """正常情况下计算 embedding 并存入数据库 + 缓存。"""
        from app.services.artwork_service import create_artwork

        artwork_data = ArtworkCreate(
            platform="pixiv",
            pid="emb_001",
            title="Test Embedding",
            author="Test Author",
            image_urls=["https://example.com/img.jpg"],
            tags=["test"],
        )
        artwork = await create_artwork(db, artwork_data)

        mock_provider = AsyncMock()
        mock_provider.embed.return_value = [[0.1, 0.2, 0.3]]

        with (
            patch("app.ai.search.get_embedding_provider", return_value=mock_provider),
            patch("app.ai.search.vector_cache") as mock_cache,
        ):
            result = await compute_and_store_embedding(db, artwork)

        assert result is True
        mock_provider.embed.assert_awaited_once()
        mock_cache.update.assert_called_once()

        # 验证数据库中有记录
        record = await db.get(ArtworkEmbedding, artwork.id)
        assert record is not None
        assert record.text_hash != ""

    async def test_compute_and_store_no_provider(self, db: AsyncSession):
        """Embedding 未启用时返回 False。"""
        artwork = _make_artwork(title="Test")
        artwork.id = 999

        with patch("app.ai.search.get_embedding_provider", return_value=None):
            result = await compute_and_store_embedding(db, artwork)

        assert result is False

    async def test_compute_and_store_skip_same_hash(self, db: AsyncSession):
        """text_hash 相同时跳过重算，返回 True。"""
        from app.services.artwork_service import create_artwork

        artwork_data = ArtworkCreate(
            platform="pixiv",
            pid="hash_001",
            title="Same Hash Test",
            author="Author",
            image_urls=["https://example.com/img.jpg"],
        )
        artwork = await create_artwork(db, artwork_data)

        mock_provider = AsyncMock()
        mock_provider.embed.return_value = [[0.1, 0.2, 0.3]]

        # 第一次计算
        with (
            patch("app.ai.search.get_embedding_provider", return_value=mock_provider),
            patch("app.ai.search.vector_cache"),
        ):
            await compute_and_store_embedding(db, artwork)

        # 第二次调用相同内容，应跳过
        with (
            patch("app.ai.search.get_embedding_provider", return_value=mock_provider),
            patch("app.ai.search.vector_cache"),
        ):
            mock_provider.embed.reset_mock()
            result = await compute_and_store_embedding(db, artwork)

        assert result is True
        mock_provider.embed.assert_not_awaited()


class TestSemanticSearch:
    async def test_semantic_search(self):
        """正常语义搜索流程。"""
        mock_provider = AsyncMock()
        mock_provider.embed.return_value = [[0.1, 0.2, 0.3]]

        mock_cache = MagicMock()
        mock_cache.search.return_value = [(1, 0.95), (2, 0.80)]

        with (
            patch("app.ai.search.get_embedding_provider", return_value=mock_provider),
            patch("app.ai.search.vector_cache", mock_cache),
        ):
            # semantic_search 需要 db 参数但此测试中不实际查询 DB
            mock_db = AsyncMock(spec=AsyncSession)
            result = await semantic_search(mock_db, "test query", top_k=5, threshold=0.5)

        assert len(result) == 2
        assert result[0] == (1, 0.95)
        mock_provider.embed.assert_awaited_once_with(["test query"])
        mock_cache.search.assert_called_once()


class TestRemoveEmbedding:
    async def test_remove_embedding(self, db: AsyncSession):
        """删除 embedding：数据库记录移除 + 缓存移除。"""
        from app.services.artwork_service import create_artwork

        artwork_data = ArtworkCreate(
            platform="pixiv",
            pid="rm_001",
            title="Remove Test",
            author="Author",
            image_urls=["https://example.com/img.jpg"],
        )
        artwork = await create_artwork(db, artwork_data)

        # 先插入一条 embedding 记录
        embedding_bytes = np.array([0.1, 0.2, 0.3], dtype=np.float32).tobytes()
        db.add(ArtworkEmbedding(artwork_id=artwork.id, text_hash="abc", embedding=embedding_bytes))
        await db.flush()

        with patch("app.ai.search.vector_cache") as mock_cache:
            await remove_embedding(db, artwork.id)

        mock_cache.remove.assert_called_once_with(artwork.id)

        # 验证数据库记录已删除
        record = await db.get(ArtworkEmbedding, artwork.id)
        assert record is None
