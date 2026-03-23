"""AI 标签建议服务单元测试。"""

import json
from unittest.mock import AsyncMock, patch

from app.ai.tagger import suggest_tags


class TestSuggestTags:
    async def test_suggest_tags_success(self):
        """LLM 正常返回标签 JSON。"""
        llm_response = json.dumps(
            [
                {"name": "风景", "type": "general", "confidence": 0.9},
                {"name": "日落", "type": "general", "confidence": 0.8},
            ]
        )
        mock_llm = AsyncMock()
        mock_llm.complete_with_images.return_value = llm_response

        with patch("app.ai.tagger.get_llm_provider", return_value=mock_llm):
            result = await suggest_tags(
                image_bytes=[b"fake_image_data"],
                existing_tags=[],
                platform="pixiv",
            )

        assert len(result) == 2
        assert result[0]["name"] == "风景"
        assert result[0]["confidence"] == 0.9
        mock_llm.complete_with_images.assert_awaited_once()

    async def test_suggest_tags_no_provider(self):
        """LLM 未启用时返回空列表。"""
        with patch("app.ai.tagger.get_llm_provider", return_value=None):
            result = await suggest_tags(image_bytes=[b"fake_image_data"])

        assert result == []

    async def test_suggest_tags_no_images(self):
        """无图片时返回空列表。"""
        mock_llm = AsyncMock()
        with patch("app.ai.tagger.get_llm_provider", return_value=mock_llm):
            result = await suggest_tags(image_bytes=[], existing_tags=[])

        assert result == []

    async def test_suggest_tags_filters_existing(self):
        """已有标签应被过滤。"""
        llm_response = json.dumps(
            [
                {"name": "风景", "type": "general", "confidence": 0.9},
                {"name": "existing_tag", "type": "general", "confidence": 0.8},
            ]
        )
        mock_llm = AsyncMock()
        mock_llm.complete_with_images.return_value = llm_response

        with patch("app.ai.tagger.get_llm_provider", return_value=mock_llm):
            result = await suggest_tags(
                image_bytes=[b"fake_image_data"],
                existing_tags=["existing_tag"],
            )

        assert len(result) == 1
        assert result[0]["name"] == "风景"

    async def test_suggest_tags_json_error(self):
        """LLM 返回非法 JSON 时返回空列表。"""
        mock_llm = AsyncMock()
        mock_llm.complete_with_images.return_value = "this is not json"

        with patch("app.ai.tagger.get_llm_provider", return_value=mock_llm):
            result = await suggest_tags(
                image_bytes=[b"fake_image_data"],
                existing_tags=[],
            )

        assert result == []
