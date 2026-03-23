"""爬虫分发器（crawlers/__init__.py）单元测试。"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from app.crawlers import CrawlResult, crawl, try_extract_identity

# ---------- try_extract_identity ----------


def test_try_extract_identity_pixiv() -> None:
    result = try_extract_identity("https://www.pixiv.net/artworks/12345")
    assert result == ("pixiv", "12345")


def test_try_extract_identity_twitter() -> None:
    result = try_extract_identity("https://x.com/user/status/67890")
    assert result == ("twitter", "67890")


def test_try_extract_identity_miyoushe() -> None:
    result = try_extract_identity("https://www.miyoushe.com/ys/article/54064752")
    assert result == ("miyoushe", "54064752")


def test_try_extract_identity_bilibili() -> None:
    result = try_extract_identity("https://t.bilibili.com/1234567890")
    assert result == ("bilibili", "1234567890")


def test_try_extract_identity_unknown() -> None:
    # gallery-dl 匹配但 extract_identity 返回 None（基类默认）
    result = try_extract_identity("https://some-random-site.com/page")
    assert result is None


# ---------- crawl ----------


async def test_crawl_dispatches() -> None:
    fake_result = CrawlResult(success=True, platform="pixiv", pid="12345")

    with patch(
        "app.crawlers.pixiv.PixivCrawler.fetch",
        new_callable=AsyncMock,
        return_value=fake_result,
    ) as mock_fetch:
        result = await crawl("https://www.pixiv.net/artworks/12345")

    mock_fetch.assert_called_once_with("https://www.pixiv.net/artworks/12345")
    assert result.success is True
    assert result.platform == "pixiv"
