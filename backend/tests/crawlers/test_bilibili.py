"""BiliBiliCrawler 单元测试。

使用基于真实 B站 API 响应结构的 fixture 数据，覆盖：
- URL 匹配 / 身份提取
- MAJOR_TYPE_OPUS 格式（features 含 itemOpusStyle 时的默认格式）
- MAJOR_TYPE_DRAW 格式（经典格式兼容）
- 标签提取、URL https 补全
- 无图片 / API 错误 / 非 200 响应
"""

from __future__ import annotations

from typing import Any

import pytest
import respx
from httpx import Response

from app.crawlers.bilibili import _API_URL, BiliBiliCrawler

# ---------- 真实动态 ID ----------
# 来源: https://t.bilibili.com/1182954050553905170
_REAL_DYNAMIC_ID = "1182954050553905170"


@pytest.fixture
def crawler() -> BiliBiliCrawler:
    return BiliBiliCrawler()


# =====================================================================
# 响应构造辅助
# =====================================================================


def _make_opus_response(
    *,
    dynamic_id: str = _REAL_DYNAMIC_ID,
    author_name: str = "Kieed",
    author_mid: int = 25589919,
    pics: list[dict[str, Any]] | None = None,
    summary_text: str = "芜~",
    opus_title: str | None = None,
    code: int = 0,
    message: str = "0",
) -> dict[str, Any]:
    """构建 MAJOR_TYPE_OPUS 格式的 API 响应（真实默认格式）。"""
    if pics is None:
        pics = [
            {
                "height": 1800,
                "size": 1813.96484375,
                "url": "http://i0.hdslb.com/bfs/new_dyn/7410b188a93dcfa5da88a96fc063164125589919.jpg",
                "width": 1056,
            },
        ]
    return {
        "code": code,
        "message": message,
        "ttl": 1,
        "data": {
            "item": {
                "id_str": dynamic_id,
                "type": "DYNAMIC_TYPE_DRAW",
                "modules": {
                    "module_author": {
                        "name": author_name,
                        "mid": author_mid,
                        "face": "https://i0.hdslb.com/bfs/face/example.jpg",
                        "pub_ts": 1774266353,
                    },
                    "module_dynamic": {
                        "additional": None,
                        "desc": None,
                        "major": {
                            "opus": {
                                "jump_url": f"//www.bilibili.com/opus/{dynamic_id}",
                                "pics": pics,
                                "summary": {"text": summary_text},
                                "title": opus_title,
                            },
                            "type": "MAJOR_TYPE_OPUS",
                        },
                        "topic": None,
                    },
                    "module_stat": {
                        "comment": {"count": 55, "forbidden": False},
                        "forward": {"count": 55, "forbidden": False},
                        "like": {"count": 1934, "forbidden": False, "status": False},
                    },
                },
                "visible": True,
            },
        },
    }


def _make_draw_response(
    *,
    dynamic_id: str = _REAL_DYNAMIC_ID,
    desc: dict[str, Any] | None = None,
    author_name: str = "画师A",
    author_mid: int = 12345,
    draw_items: list[dict[str, Any]] | None = None,
    code: int = 0,
    message: str = "0",
) -> dict[str, Any]:
    """构建 MAJOR_TYPE_DRAW 格式的 API 响应（经典格式）。"""
    if draw_items is None:
        draw_items = [
            {"src": "https://i0.hdslb.com/bfs/new_dyn/img1.jpg"},
            {"src": "https://i0.hdslb.com/bfs/new_dyn/img2.jpg"},
        ]
    return {
        "code": code,
        "message": message,
        "ttl": 1,
        "data": {
            "item": {
                "id_str": dynamic_id,
                "type": "DYNAMIC_TYPE_DRAW",
                "modules": {
                    "module_author": {
                        "name": author_name,
                        "mid": author_mid,
                    },
                    "module_dynamic": {
                        "additional": None,
                        "desc": desc,
                        "major": {
                            "draw": {"id": 388928160, "items": draw_items},
                            "type": "MAJOR_TYPE_DRAW",
                        },
                        "topic": None,
                    },
                },
                "visible": True,
            },
        },
    }


def _api_url(dynamic_id: str) -> str:
    return _API_URL.format(dynamic_id=dynamic_id)


# =====================================================================
# URL 匹配
# =====================================================================


class TestMatch:
    def test_t_bilibili(self, crawler: BiliBiliCrawler) -> None:
        assert crawler.match(f"https://t.bilibili.com/{_REAL_DYNAMIC_ID}") is True

    def test_opus(self, crawler: BiliBiliCrawler) -> None:
        assert crawler.match(f"https://www.bilibili.com/opus/{_REAL_DYNAMIC_ID}") is True
        assert crawler.match(f"https://bilibili.com/opus/{_REAL_DYNAMIC_ID}") is True

    def test_no_match(self, crawler: BiliBiliCrawler) -> None:
        assert crawler.match("https://twitter.com/x/status/123") is False
        assert crawler.match("https://www.bilibili.com/video/BV12345") is False


# =====================================================================
# 身份提取
# =====================================================================


class TestExtractIdentity:
    def test_t_bilibili(self, crawler: BiliBiliCrawler) -> None:
        result = crawler.extract_identity(f"https://t.bilibili.com/{_REAL_DYNAMIC_ID}")
        assert result == ("bilibili", _REAL_DYNAMIC_ID)

    def test_opus(self, crawler: BiliBiliCrawler) -> None:
        result = crawler.extract_identity(f"https://www.bilibili.com/opus/{_REAL_DYNAMIC_ID}")
        assert result == ("bilibili", _REAL_DYNAMIC_ID)

    def test_no_match_returns_none(self, crawler: BiliBiliCrawler) -> None:
        assert crawler.extract_identity("https://example.com") is None


# =====================================================================
# 抓取 — MAJOR_TYPE_OPUS（真实默认格式）
# =====================================================================


class TestFetchOpus:
    """模拟真实动态 t.bilibili.com/1182954050553905170 的 opus 格式响应。"""

    @respx.mock
    async def test_success(self, crawler: BiliBiliCrawler) -> None:
        """基本的 opus 格式抓取。"""
        respx.get(_api_url(_REAL_DYNAMIC_ID)).mock(
            return_value=Response(200, json=_make_opus_response()),
        )

        result = await crawler.fetch(f"https://t.bilibili.com/{_REAL_DYNAMIC_ID}")

        assert result.success is True
        assert result.platform == "bilibili"
        assert result.pid == _REAL_DYNAMIC_ID
        assert result.author == "Kieed"
        assert result.author_id == "25589919"
        assert result.title == "芜~"
        assert len(result.image_urls) == 1
        assert result.source_url == f"https://t.bilibili.com/{_REAL_DYNAMIC_ID}"

    @respx.mock
    async def test_http_url_converted_to_https(self, crawler: BiliBiliCrawler) -> None:
        """opus.pics[].url 的 http:// 应转为 https://。"""
        respx.get(_api_url(_REAL_DYNAMIC_ID)).mock(
            return_value=Response(200, json=_make_opus_response()),
        )

        result = await crawler.fetch(f"https://t.bilibili.com/{_REAL_DYNAMIC_ID}")

        assert result.success is True
        assert all(u.startswith("https://") for u in result.image_urls)

    @respx.mock
    async def test_protocol_relative_url(self, crawler: BiliBiliCrawler) -> None:
        """以 // 开头的图片 URL 应补全为 https://。"""
        respx.get(_api_url(_REAL_DYNAMIC_ID)).mock(
            return_value=Response(
                200,
                json=_make_opus_response(
                    pics=[{"url": "//i0.hdslb.com/bfs/new_dyn/test.jpg"}],
                ),
            ),
        )

        result = await crawler.fetch(f"https://t.bilibili.com/{_REAL_DYNAMIC_ID}")

        assert result.success is True
        assert result.image_urls[0] == "https://i0.hdslb.com/bfs/new_dyn/test.jpg"

    @respx.mock
    async def test_opus_title_prepended(self, crawler: BiliBiliCrawler) -> None:
        """opus.title 存在时应作为标题优先使用。"""
        respx.get(_api_url(_REAL_DYNAMIC_ID)).mock(
            return_value=Response(
                200,
                json=_make_opus_response(opus_title="画了一张甘雨", summary_text="正文内容"),
            ),
        )

        result = await crawler.fetch(f"https://t.bilibili.com/{_REAL_DYNAMIC_ID}")

        assert result.success is True
        assert result.title == "画了一张甘雨"

    @respx.mock
    async def test_tag_extraction_from_summary(self, crawler: BiliBiliCrawler) -> None:
        """从 opus summary 正文中提取 #标签#。"""
        respx.get(_api_url(_REAL_DYNAMIC_ID)).mock(
            return_value=Response(
                200,
                json=_make_opus_response(summary_text="新作品 #原神# #甘雨# 大家看看"),
            ),
        )

        result = await crawler.fetch(f"https://t.bilibili.com/{_REAL_DYNAMIC_ID}")

        assert result.success is True
        assert "原神" in result.tags
        assert "甘雨" in result.tags

    @respx.mock
    async def test_empty_summary(self, crawler: BiliBiliCrawler) -> None:
        """summary.text 为空时不应崩溃。"""
        respx.get(_api_url(_REAL_DYNAMIC_ID)).mock(
            return_value=Response(
                200,
                json=_make_opus_response(summary_text=""),
            ),
        )

        result = await crawler.fetch(f"https://t.bilibili.com/{_REAL_DYNAMIC_ID}")

        assert result.success is True
        assert result.title == ""
        assert result.tags == []


# =====================================================================
# 抓取 — MAJOR_TYPE_DRAW（经典格式兼容）
# =====================================================================


class TestFetchDraw:
    @respx.mock
    async def test_success(self, crawler: BiliBiliCrawler) -> None:
        respx.get(_api_url(_REAL_DYNAMIC_ID)).mock(
            return_value=Response(200, json=_make_draw_response()),
        )

        result = await crawler.fetch(f"https://t.bilibili.com/{_REAL_DYNAMIC_ID}")

        assert result.success is True
        assert len(result.image_urls) == 2
        assert result.author == "画师A"

    @respx.mock
    async def test_desc_text_as_title(self, crawler: BiliBiliCrawler) -> None:
        respx.get(_api_url(_REAL_DYNAMIC_ID)).mock(
            return_value=Response(
                200,
                json=_make_draw_response(desc={"text": "今天画的新图\n第二行内容"}),
            ),
        )

        result = await crawler.fetch(f"https://t.bilibili.com/{_REAL_DYNAMIC_ID}")

        assert result.success is True
        assert result.title == "今天画的新图"

    @respx.mock
    async def test_null_desc(self, crawler: BiliBiliCrawler) -> None:
        """draw 格式下 desc 为 null 时不应崩溃。"""
        respx.get(_api_url(_REAL_DYNAMIC_ID)).mock(
            return_value=Response(200, json=_make_draw_response(desc=None)),
        )

        result = await crawler.fetch(f"https://t.bilibili.com/{_REAL_DYNAMIC_ID}")

        assert result.success is True
        assert result.title == ""

    @respx.mock
    async def test_tag_extraction(self, crawler: BiliBiliCrawler) -> None:
        respx.get(_api_url(_REAL_DYNAMIC_ID)).mock(
            return_value=Response(
                200,
                json=_make_draw_response(desc={"text": "新作品 #原神# #甘雨# 大家看看"}),
            ),
        )

        result = await crawler.fetch(f"https://t.bilibili.com/{_REAL_DYNAMIC_ID}")

        assert result.success is True
        assert "原神" in result.tags
        assert "甘雨" in result.tags


# =====================================================================
# 抓取 — 错误场景
# =====================================================================


class TestFetchErrors:
    @respx.mock
    async def test_no_images_opus(self, crawler: BiliBiliCrawler) -> None:
        respx.get(_api_url(_REAL_DYNAMIC_ID)).mock(
            return_value=Response(200, json=_make_opus_response(pics=[])),
        )

        result = await crawler.fetch(f"https://t.bilibili.com/{_REAL_DYNAMIC_ID}")

        assert result.success is False
        assert "图片" in result.error

    @respx.mock
    async def test_no_images_draw(self, crawler: BiliBiliCrawler) -> None:
        respx.get(_api_url(_REAL_DYNAMIC_ID)).mock(
            return_value=Response(200, json=_make_draw_response(draw_items=[])),
        )

        result = await crawler.fetch(f"https://t.bilibili.com/{_REAL_DYNAMIC_ID}")

        assert result.success is False
        assert "图片" in result.error

    @respx.mock
    async def test_api_error_code(self, crawler: BiliBiliCrawler) -> None:
        respx.get(_api_url(_REAL_DYNAMIC_ID)).mock(
            return_value=Response(
                200,
                json=_make_opus_response(code=-400, message="请求错误"),
            ),
        )

        result = await crawler.fetch(f"https://t.bilibili.com/{_REAL_DYNAMIC_ID}")

        assert result.success is False
        assert "请求错误" in result.error

    @respx.mock
    async def test_non_200_status(self, crawler: BiliBiliCrawler) -> None:
        respx.get(_api_url(_REAL_DYNAMIC_ID)).mock(
            return_value=Response(502, text="Bad Gateway"),
        )

        result = await crawler.fetch(f"https://t.bilibili.com/{_REAL_DYNAMIC_ID}")

        assert result.success is False
        assert "502" in result.error

    async def test_invalid_url(self, crawler: BiliBiliCrawler) -> None:
        result = await crawler.fetch("https://example.com/not-bilibili")

        assert result.success is False
        assert "ID" in result.error
