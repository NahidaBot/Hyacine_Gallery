"""PixivCrawler 单元测试。"""

from __future__ import annotations

import pytest
import respx
from httpx import Response

from app.crawlers.pixiv import PixivCrawler


@pytest.fixture
def crawler() -> PixivCrawler:
    return PixivCrawler()


# ---------- match ----------


def test_match_pixiv_urls(crawler: PixivCrawler) -> None:
    assert crawler.match("https://www.pixiv.net/artworks/12345") is True
    assert crawler.match("https://pixiv.net/en/artworks/67890") is True


def test_match_phixiv(crawler: PixivCrawler) -> None:
    assert crawler.match("https://phixiv.net/artworks/12345") is True


def test_no_match(crawler: PixivCrawler) -> None:
    assert crawler.match("https://twitter.com/x/status/123") is False


# ---------- extract_identity ----------


def test_extract_identity(crawler: PixivCrawler) -> None:
    result = crawler.extract_identity("https://www.pixiv.net/artworks/12345")
    assert result == ("pixiv", "12345")


def test_extract_identity_none(crawler: PixivCrawler) -> None:
    result = crawler.extract_identity("https://twitter.com/x/status/123")
    assert result is None


# ---------- fetch ----------


def _make_detail_body(
    *,
    pid: str = "12345",
    title: str = "テスト作品",
    user_name: str = "テストユーザー",
    user_id: int = 999,
    x_restrict: int = 0,
    ai_type: int = 0,
    width: int = 1920,
    height: int = 1080,
    tags: list[dict] | None = None,
) -> dict:
    if tags is None:
        tags = [
            {
                "tag": "オリジナル",
                "translation": {"zh": "原创", "en": "original"},
            },
            {
                "tag": "原神",
                "translation": {"en": "Genshin Impact"},
            },
            {
                "tag": "1000users入り",
                "translation": {},
            },
        ]
    return {
        "error": False,
        "body": {
            "id": pid,
            "title": title,
            "userName": user_name,
            "userId": user_id,
            "xRestrict": x_restrict,
            "aiType": ai_type,
            "width": width,
            "height": height,
            "tags": {
                "tags": tags,
            },
        },
    }


def _make_pages_body(count: int = 2) -> dict:
    return {
        "error": False,
        "body": [
            {
                "urls": {
                    "original": f"https://i.pximg.net/img-original/img/2024/01/01/00/00/00/12345_p{i}.png",
                }
            }
            for i in range(count)
        ],
    }


@respx.mock
async def test_fetch_success(crawler: PixivCrawler) -> None:
    pid = "12345"
    respx.get(f"https://www.pixiv.net/ajax/illust/{pid}?lang=zh").mock(
        return_value=Response(200, json=_make_detail_body(pid=pid))
    )
    respx.get(f"https://www.pixiv.net/ajax/illust/{pid}/pages?lang=zh").mock(
        return_value=Response(200, json=_make_pages_body(2))
    )

    result = await crawler.fetch(f"https://www.pixiv.net/artworks/{pid}")

    assert result.success is True
    assert result.platform == "pixiv"
    assert result.pid == pid
    assert result.title == "テスト作品"
    assert result.author == "テストユーザー"
    assert result.is_nsfw is False
    assert result.is_ai is False
    assert len(result.image_urls) == 2
    # 中文翻译优先: オリジナル → 原创
    assert "原创" in result.tags
    # 原神 含中文，保留原 tag 而非 Genshin Impact
    assert "原神" in result.tags
    # users入り 标签应被过滤
    assert all("users入り" not in t for t in result.tags)
    assert result.width == 1920
    assert result.height == 1080


@respx.mock
async def test_fetch_r18(crawler: PixivCrawler) -> None:
    pid = "99999"
    respx.get(f"https://www.pixiv.net/ajax/illust/{pid}?lang=zh").mock(
        return_value=Response(200, json=_make_detail_body(pid=pid, x_restrict=1))
    )
    respx.get(f"https://www.pixiv.net/ajax/illust/{pid}/pages?lang=zh").mock(
        return_value=Response(200, json=_make_pages_body(1))
    )

    result = await crawler.fetch(f"https://www.pixiv.net/artworks/{pid}")

    assert result.success is True
    assert result.is_nsfw is True


@respx.mock
async def test_fetch_ai(crawler: PixivCrawler) -> None:
    pid = "88888"
    respx.get(f"https://www.pixiv.net/ajax/illust/{pid}?lang=zh").mock(
        return_value=Response(200, json=_make_detail_body(pid=pid, ai_type=2))
    )
    respx.get(f"https://www.pixiv.net/ajax/illust/{pid}/pages?lang=zh").mock(
        return_value=Response(200, json=_make_pages_body(1))
    )

    result = await crawler.fetch(f"https://www.pixiv.net/artworks/{pid}")

    assert result.success is True
    assert result.is_ai is True


@respx.mock
async def test_fetch_error(crawler: PixivCrawler) -> None:
    pid = "00000"
    respx.get(f"https://www.pixiv.net/ajax/illust/{pid}?lang=zh").mock(
        return_value=Response(
            200,
            json={"error": True, "message": "该作品已被删除"},
        )
    )

    result = await crawler.fetch(f"https://www.pixiv.net/artworks/{pid}")

    assert result.success is False
    assert "该作品已被删除" in result.error


async def test_fetch_no_pid(crawler: PixivCrawler) -> None:
    result = await crawler.fetch("https://example.com/not-pixiv")

    assert result.success is False
    assert "无法提取" in result.error
