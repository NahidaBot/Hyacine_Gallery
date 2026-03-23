"""GalleryDLCrawler 单元测试。"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest

from app.crawlers.gallery_dl import GalleryDLCrawler


@pytest.fixture
def crawler() -> GalleryDLCrawler:
    return GalleryDLCrawler()


# ---------- match ----------


def test_match_always(crawler: GalleryDLCrawler) -> None:
    assert crawler.match("https://example.com/anything") is True
    assert crawler.match("https://pixiv.net/artworks/12345") is True
    assert crawler.match("literally anything") is True


# ---------- fetch ----------


def _make_process_mock(
    *,
    returncode: int = 0,
    stdout: bytes = b"",
    stderr: bytes = b"",
) -> AsyncMock:
    """创建模拟的 asyncio.subprocess 进程对象。"""
    proc = AsyncMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    return proc


async def test_fetch_success(crawler: GalleryDLCrawler) -> None:
    entries = [
        [
            "/tmp/gallery-dl",
            {"category": "danbooru", "id": 12345, "title": "Test Image", "author": "artist1"},
            "https://cdn.example.com/img1.jpg",
        ],
        [
            "/tmp/gallery-dl",
            {"category": "danbooru", "id": 12345, "title": "Test Image", "author": "artist1"},
            "https://cdn.example.com/img2.jpg",
        ],
    ]
    stdout = "\n".join(json.dumps(e) for e in entries).encode()
    proc = _make_process_mock(returncode=0, stdout=stdout)

    with patch("asyncio.create_subprocess_exec", return_value=proc) as mock_exec:
        result = await crawler.fetch("https://danbooru.donmai.us/posts/12345")

    mock_exec.assert_called_once_with(
        "gallery-dl",
        "--dump-json",
        "--no-download",
        "https://danbooru.donmai.us/posts/12345",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    assert result.success is True
    assert result.platform == "danbooru"
    assert result.pid == "12345"
    assert result.title == "Test Image"
    assert result.author == "artist1"
    assert len(result.image_urls) == 2
    assert result.image_urls[0] == "https://cdn.example.com/img1.jpg"


async def test_fetch_failure(crawler: GalleryDLCrawler) -> None:
    proc = _make_process_mock(returncode=1, stderr=b"No suitable extractor found")

    with patch("asyncio.create_subprocess_exec", return_value=proc):
        result = await crawler.fetch("https://unknown-site.com/page")

    assert result.success is False
    assert "No suitable extractor found" in result.error


async def test_fetch_not_installed(crawler: GalleryDLCrawler) -> None:
    with patch(
        "asyncio.create_subprocess_exec",
        side_effect=FileNotFoundError("gallery-dl not found"),
    ):
        result = await crawler.fetch("https://example.com/something")

    assert result.success is False
    assert "未安装" in result.error
