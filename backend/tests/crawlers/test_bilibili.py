"""BiliBiliCrawler 单元测试。"""

from __future__ import annotations

import pytest
import respx
from httpx import Response

from app.crawlers.bilibili import BiliBiliCrawler


@pytest.fixture
def crawler() -> BiliBiliCrawler:
    return BiliBiliCrawler()


# ---------- match ----------


def test_match_t_bilibili(crawler: BiliBiliCrawler) -> None:
    assert crawler.match("https://t.bilibili.com/1234567890") is True


def test_match_opus(crawler: BiliBiliCrawler) -> None:
    assert crawler.match("https://www.bilibili.com/opus/1234567890") is True
    assert crawler.match("https://bilibili.com/opus/1234567890") is True


def test_no_match(crawler: BiliBiliCrawler) -> None:
    assert crawler.match("https://twitter.com/x/status/123") is False
    assert crawler.match("https://www.bilibili.com/video/BV12345") is False


# ---------- extract_identity ----------


def test_extract_identity(crawler: BiliBiliCrawler) -> None:
    result = crawler.extract_identity("https://t.bilibili.com/1234567890")
    assert result == ("bilibili", "1234567890")

    result2 = crawler.extract_identity("https://www.bilibili.com/opus/9876543210")
    assert result2 == ("bilibili", "9876543210")


def test_extract_identity_none(crawler: BiliBiliCrawler) -> None:
    result = crawler.extract_identity("https://example.com")
    assert result is None


# ---------- fetch ----------


def _make_dynamic_response(
    *,
    dynamic_id: str = "1234567890",
    text: str = "今天画的图 #原神# #甘雨#",
    author_name: str = "画师A",
    author_mid: int = 12345,
    draw_items: list[dict] | None = None,
    code: int = 0,
    message: str = "0",
) -> dict:
    if draw_items is None:
        draw_items = [
            {"src": "https://i0.hdslb.com/bfs/new_dyn/img1.jpg"},
            {"src": "https://i0.hdslb.com/bfs/new_dyn/img2.jpg"},
        ]
    return {
        "code": code,
        "message": message,
        "data": {
            "item": {
                "id_str": dynamic_id,
                "modules": {
                    "module_author": {
                        "name": author_name,
                        "mid": author_mid,
                    },
                    "module_dynamic": {
                        "desc": {
                            "text": text,
                        },
                        "major": {
                            "draw": {
                                "items": draw_items,
                            },
                        },
                    },
                },
            },
        },
    }


@respx.mock
async def test_fetch_success(crawler: BiliBiliCrawler) -> None:
    dynamic_id = "1234567890"
    respx.get(f"https://api.bilibili.com/x/polymer/web-dynamic/v1/detail?id={dynamic_id}").mock(
        return_value=Response(200, json=_make_dynamic_response(dynamic_id=dynamic_id))
    )

    result = await crawler.fetch(f"https://t.bilibili.com/{dynamic_id}")

    assert result.success is True
    assert result.platform == "bilibili"
    assert result.pid == dynamic_id
    assert result.author == "画师A"
    assert result.author_id == "12345"
    assert len(result.image_urls) == 2
    assert result.source_url == f"https://t.bilibili.com/{dynamic_id}"


@respx.mock
async def test_fetch_tag_extraction(crawler: BiliBiliCrawler) -> None:
    dynamic_id = "1111111111"
    respx.get(f"https://api.bilibili.com/x/polymer/web-dynamic/v1/detail?id={dynamic_id}").mock(
        return_value=Response(
            200,
            json=_make_dynamic_response(
                dynamic_id=dynamic_id,
                text="新作品 #原神# #甘雨# 大家看看",
            ),
        )
    )

    result = await crawler.fetch(f"https://t.bilibili.com/{dynamic_id}")

    assert result.success is True
    assert "原神" in result.tags
    assert "甘雨" in result.tags


@respx.mock
async def test_fetch_no_images(crawler: BiliBiliCrawler) -> None:
    dynamic_id = "2222222222"
    respx.get(f"https://api.bilibili.com/x/polymer/web-dynamic/v1/detail?id={dynamic_id}").mock(
        return_value=Response(
            200,
            json=_make_dynamic_response(dynamic_id=dynamic_id, draw_items=[]),
        )
    )

    result = await crawler.fetch(f"https://t.bilibili.com/{dynamic_id}")

    assert result.success is False
    assert "图片" in result.error
