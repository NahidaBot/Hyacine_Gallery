"""MiYouSheCrawler 单元测试。"""

from __future__ import annotations

import pytest
import respx
from httpx import Response

from app.crawlers.miyoushe import MiYouSheCrawler


@pytest.fixture
def crawler() -> MiYouSheCrawler:
    return MiYouSheCrawler()


# ---------- match ----------


def test_match_miyoushe(crawler: MiYouSheCrawler) -> None:
    assert crawler.match("https://www.miyoushe.com/ys/article/54064752") is True
    assert crawler.match("https://miyoushe.com/sr/article/12345") is True


def test_match_hoyolab(crawler: MiYouSheCrawler) -> None:
    assert crawler.match("https://www.hoyolab.com/article/30083385") is True
    assert crawler.match("https://hoyolab.com/article/99999") is True


def test_match_mihoyo(crawler: MiYouSheCrawler) -> None:
    assert crawler.match("https://bbs.mihoyo.com/ys/article/54064752") is True


def test_no_match(crawler: MiYouSheCrawler) -> None:
    assert crawler.match("https://twitter.com/x/status/123") is False
    assert crawler.match("https://pixiv.net/artworks/12345") is False


# ---------- extract_identity ----------


def test_extract_identity(crawler: MiYouSheCrawler) -> None:
    result = crawler.extract_identity("https://www.miyoushe.com/ys/article/54064752")
    assert result == ("miyoushe", "54064752")


def test_extract_identity_none(crawler: MiYouSheCrawler) -> None:
    result = crawler.extract_identity("https://example.com")
    assert result is None


# ---------- fetch ----------


def _make_cn_response(
    *,
    post_id: str = "54064752",
    title: str = "测试帖子",
    nickname: str = "旅行者",
    uid: int = 12345,
    game_id: int = 2,
    images: list[dict] | None = None,
    topics: list[dict] | None = None,
    retcode: int = 0,
    message: str = "OK",
) -> dict:
    if images is None:
        images = [
            {"url": "https://upload-bbs.miyoushe.com/img1.jpg", "width": 1920, "height": 1080},
            {"url": "https://upload-bbs.miyoushe.com/img2.jpg", "width": 1920, "height": 1080},
        ]
    if topics is None:
        topics = [
            {"name": "原神同人"},
            {"name": "甘雨"},
        ]
    return {
        "retcode": retcode,
        "message": message,
        "data": {
            "post": {
                "post": {
                    "post_id": post_id,
                    "subject": title,
                    "game_id": game_id,
                },
                "user": {
                    "nickname": nickname,
                    "uid": uid,
                },
                "image_list": images,
                "topics": topics,
            },
        },
    }


@respx.mock
async def test_fetch_cn_success(crawler: MiYouSheCrawler) -> None:
    post_id = "54064752"
    respx.get(f"https://bbs-api.miyoushe.com/post/wapi/getPostFull?post_id={post_id}").mock(
        return_value=Response(200, json=_make_cn_response(post_id=post_id))
    )

    result = await crawler.fetch(f"https://www.miyoushe.com/ys/article/{post_id}")

    assert result.success is True
    assert result.platform == "miyoushe"
    assert result.pid == post_id
    assert result.title == "测试帖子"
    assert result.author == "旅行者"
    assert len(result.image_urls) == 2
    # 话题标签 + 游戏名
    assert "原神同人" in result.tags
    assert "甘雨" in result.tags
    assert "原神" in result.tags  # game_id=2 → 原神
    assert result.source_url == f"https://www.miyoushe.com/ys/article/{post_id}"


@respx.mock
async def test_fetch_no_images(crawler: MiYouSheCrawler) -> None:
    post_id = "11111"
    respx.get(f"https://bbs-api.miyoushe.com/post/wapi/getPostFull?post_id={post_id}").mock(
        return_value=Response(200, json=_make_cn_response(post_id=post_id, images=[]))
    )

    result = await crawler.fetch(f"https://www.miyoushe.com/ys/article/{post_id}")

    assert result.success is False
    assert "图片" in result.error


@respx.mock
async def test_fetch_api_error(crawler: MiYouSheCrawler) -> None:
    post_id = "22222"
    respx.get(f"https://bbs-api.miyoushe.com/post/wapi/getPostFull?post_id={post_id}").mock(
        return_value=Response(
            200,
            json={"retcode": -1, "message": "帖子不存在", "data": None},
        )
    )

    result = await crawler.fetch(f"https://www.miyoushe.com/ys/article/{post_id}")

    assert result.success is False
    assert "帖子不存在" in result.error
