"""爬虫注册表 — 将 URL 分发到对应的平台爬虫。"""

from __future__ import annotations

from app.crawlers.base import BaseCrawler, CrawlResult
from app.crawlers.gallery_dl import GalleryDLCrawler
from app.crawlers.miyoushe import MiYouSheCrawler
from app.crawlers.pixiv import PixivCrawler
from app.crawlers.twitter import TwitterCrawler

__all__ = ["BaseCrawler", "CrawlResult", "crawl"]

# 有序列表：第一个匹配的爬虫生效，GalleryDL 作为兜底放在最后
_CRAWLERS: list[BaseCrawler] = [
    PixivCrawler(),
    TwitterCrawler(),
    MiYouSheCrawler(),
    GalleryDLCrawler(),
]


async def crawl(url: str) -> CrawlResult:
    """将 URL 分发给第一个匹配的爬虫并返回结果。"""
    for crawler in _CRAWLERS:
        if crawler.match(url):
            return await crawler.fetch(url)
    return CrawlResult(success=False, error="没有匹配该 URL 的爬虫")
