"""标题润色服务单元测试。"""

from unittest.mock import AsyncMock, patch

from app.ai.polisher import _is_mostly_chinese, polish_title


class TestIsMostlyChinese:
    def test_is_mostly_chinese_true(self):
        """纯中文文本应返回 True。"""
        assert _is_mostly_chinese("这是中文标题") is True

    def test_is_mostly_chinese_false(self):
        """纯英文文本应返回 False。"""
        assert _is_mostly_chinese("English Title") is False

    def test_is_mostly_chinese_mixed(self):
        """混合文本取决于中文字符占比是否超过阈值。"""
        # "Half中文Half" — 2 个 CJK 字符，8 个字母字符，比例 = 2/10 = 0.2 < 0.5
        assert _is_mostly_chinese("Half中文Half") is False
        # 降低阈值后可判定为中文
        assert _is_mostly_chinese("Half中文Half", threshold=0.1) is True

    def test_is_mostly_chinese_empty(self):
        """空字符串返回 False。"""
        assert _is_mostly_chinese("") is False


class TestPolishTitle:
    async def test_polish_title_skip_chinese(self):
        """已是中文标题时跳过，返回 None。"""
        result = await polish_title("这是中文标题", tags=[], platform="pixiv")
        assert result is None

    async def test_polish_title_skip_empty(self):
        """空标题返回 None。"""
        result = await polish_title("", tags=[], platform="pixiv")
        assert result is None

    async def test_polish_title_success(self):
        """LLM 正常返回翻译标题。"""
        mock_llm = AsyncMock()
        mock_llm.complete.return_value = "「翻译后的标题」"

        with patch("app.ai.polisher.get_llm_provider", return_value=mock_llm):
            result = await polish_title(
                "Sunset over the hills", tags=["landscape"], platform="pixiv"
            )

        assert result == "翻译后的标题"
        mock_llm.complete.assert_awaited_once()

    async def test_polish_title_no_provider(self):
        """LLM 未启用时返回 None。"""
        with patch("app.ai.polisher.get_llm_provider", return_value=None):
            result = await polish_title("English Title", tags=[], platform="pixiv")

        assert result is None

    async def test_polish_title_error(self):
        """LLM 抛异常时返回 None。"""
        mock_llm = AsyncMock()
        mock_llm.complete.side_effect = RuntimeError("API error")

        with patch("app.ai.polisher.get_llm_provider", return_value=mock_llm):
            result = await polish_title("English Title", tags=[], platform="pixiv")

        assert result is None
