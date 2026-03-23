"""NSFW 检测服务单元测试。"""

from unittest.mock import AsyncMock, patch

from app.ai.nsfw_detector import _detect_nsfw_llm


class TestDetectNsfwLLM:
    async def test_detect_nsfw_llm(self):
        """LLM 正常返回 NSFW 分数。"""
        mock_llm = AsyncMock()
        mock_llm.complete_with_images.return_value = "0.7"

        with patch("app.ai.factory.get_llm_provider", return_value=mock_llm):
            result = await _detect_nsfw_llm(b"fake_image_data")

        assert result == 0.7

    async def test_detect_nsfw_no_provider(self):
        """LLM 未启用时返回 0.0。"""
        with patch("app.ai.factory.get_llm_provider", return_value=None):
            result = await _detect_nsfw_llm(b"fake_image_data")

        assert result == 0.0

    async def test_detect_nsfw_parse_error(self):
        """LLM 返回非数字时返回 0.0。"""
        mock_llm = AsyncMock()
        mock_llm.complete_with_images.return_value = "not a number"

        with patch("app.ai.factory.get_llm_provider", return_value=mock_llm):
            result = await _detect_nsfw_llm(b"fake_image_data")

        assert result == 0.0
