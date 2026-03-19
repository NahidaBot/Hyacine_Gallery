"""Crawler registry — dispatches URLs to the appropriate platform crawler."""

from __future__ import annotations

from app.crawlers.base import BaseCrawler, CrawlResult
from app.crawlers.gallery_dl import GalleryDLCrawler
from app.crawlers.miyoushe import MiYouSheCrawler
from app.crawlers.pixiv import PixivCrawler
from app.crawlers.twitter import TwitterCrawler

__all__ = ["BaseCrawler", "CrawlResult", "crawl"]

# Ordered list: first match wins, GalleryDL is the fallback at the end
_CRAWLERS: list[BaseCrawler] = [
    PixivCrawler(),
    TwitterCrawler(),
    MiYouSheCrawler(),
    GalleryDLCrawler(),
]


async def crawl(url: str) -> CrawlResult:
    """Dispatch a URL to the first matching crawler and return the result."""
    for crawler in _CRAWLERS:
        if crawler.match(url):
            return await crawler.fetch(url)
    return CrawlResult(success=False, error="No crawler matched the URL")
