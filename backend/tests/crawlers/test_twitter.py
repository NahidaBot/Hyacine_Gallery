"""TwitterCrawler 单元测试。"""

from __future__ import annotations

import pytest
import respx
from httpx import ConnectError, Response

from app.crawlers.twitter import TwitterCrawler


@pytest.fixture
def crawler() -> TwitterCrawler:
    return TwitterCrawler()


# ---------- match ----------


def test_match_urls(crawler: TwitterCrawler) -> None:
    urls = [
        "https://twitter.com/user/status/123456",
        "https://x.com/user/status/123456",
        "https://fxtwitter.com/user/status/123456",
        "https://vxtwitter.com/user/status/123456",
        "https://fixupx.com/user/status/123456",
    ]
    for url in urls:
        assert crawler.match(url) is True, f"应匹配: {url}"


def test_no_match(crawler: TwitterCrawler) -> None:
    assert crawler.match("https://pixiv.net/artworks/123") is False


# ---------- extract_identity ----------


def test_extract_identity(crawler: TwitterCrawler) -> None:
    result = crawler.extract_identity("https://x.com/artist/status/789012")
    assert result == ("twitter", "789012")


def test_extract_identity_none(crawler: TwitterCrawler) -> None:
    result = crawler.extract_identity("https://pixiv.net/artworks/123")
    assert result is None


# ---------- fetch ----------


def _make_tweet_response(
    *,
    tweet_id: str = "123456",
    text: str = "好看的图",
    author_name: str = "画师",
    author_screen: str = "artist",
    photos: list[dict] | None = None,
    possibly_sensitive: bool = False,
) -> dict:
    if photos is None:
        photos = [
            {"url": "https://pbs.twimg.com/media/img1.jpg"},
            {"url": "https://pbs.twimg.com/media/img2.jpg"},
        ]
    return {
        "tweet": {
            "id": tweet_id,
            "text": text,
            "author": {
                "name": author_name,
                "screen_name": author_screen,
            },
            "media": {
                "photos": photos,
            },
            "possibly_sensitive": possibly_sensitive,
        },
    }


@respx.mock
async def test_fetch_success(crawler: TwitterCrawler) -> None:
    respx.get("https://api.fxtwitter.com/artist/status/123456").mock(
        return_value=Response(200, json=_make_tweet_response())
    )

    result = await crawler.fetch("https://x.com/artist/status/123456")

    assert result.success is True
    assert result.platform == "twitter"
    assert result.pid == "123456"
    assert result.author == "画师"
    assert result.author_id == "artist"
    assert len(result.image_urls) == 2
    assert result.is_nsfw is False
    assert result.source_url == "https://x.com/artist/status/123456"


@respx.mock
async def test_fetch_no_photos(crawler: TwitterCrawler) -> None:
    respx.get("https://api.fxtwitter.com/user/status/111").mock(
        return_value=Response(200, json=_make_tweet_response(tweet_id="111", photos=[]))
    )

    result = await crawler.fetch("https://x.com/user/status/111")

    assert result.success is False
    assert "图片" in result.error


@respx.mock
async def test_fetch_http_error(crawler: TwitterCrawler) -> None:
    respx.get("https://api.fxtwitter.com/user/status/222").mock(
        side_effect=ConnectError("连接失败")
    )

    result = await crawler.fetch("https://x.com/user/status/222")

    assert result.success is False
    assert "失败" in result.error
