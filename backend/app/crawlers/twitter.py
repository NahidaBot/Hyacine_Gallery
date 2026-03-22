"""Twitter/X 爬虫，使用 fxtwitter.com API（无需认证）。"""

from __future__ import annotations

import logging
import re

import httpx

from app.crawlers.base import BaseCrawler, CrawlResult

logger = logging.getLogger(__name__)

_TWITTER_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.)?(?:twitter\.com|x\.com|fxtwitter\.com|vxtwitter\.com|fixupx\.com)"
    r"/(\w+)/status/(\d+)"
)

_FX_API = "https://api.fxtwitter.com/{user}/status/{tweet_id}"


def _extract_info(url: str) -> tuple[str, str] | None:
    m = _TWITTER_PATTERN.search(url)
    if m:
        return m.group(1), m.group(2)
    return None


class TwitterCrawler(BaseCrawler):
    def match(self, url: str) -> bool:
        return _extract_info(url) is not None

    def extract_identity(self, url: str) -> tuple[str, str] | None:
        info = _extract_info(url)
        return ("twitter", info[1]) if info else None

    async def fetch(self, url: str) -> CrawlResult:
        info = _extract_info(url)
        if not info:
            logger.info("URL 不匹配 Twitter 格式: %s", url)
            return CrawlResult(success=False, error="无法提取推文信息")

        user, tweet_id = info
        logger.info("Twitter 抓取: user=%s, tweet_id=%s", user, tweet_id)

        api_url = _FX_API.format(user=user, tweet_id=tweet_id)
        logger.info("请求 fxtwitter API: %s", api_url)

        async with httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
            },
        ) as client:
            try:
                resp = await client.get(api_url)
            except httpx.HTTPError as e:
                logger.info("fxtwitter 请求失败: %s", e)
                return CrawlResult(success=False, error=f"fxtwitter 请求失败: {e}")

            logger.info("fxtwitter 响应: status=%d, length=%d", resp.status_code, len(resp.content))

            if resp.status_code != 200:
                logger.info("fxtwitter 错误响应体: %s", resp.text[:500])
                return CrawlResult(
                    success=False,
                    error=f"fxtwitter API 返回 {resp.status_code}: {resp.text[:200]}",
                )

            data = resp.json()
            logger.info("fxtwitter 响应字段: %s", list(data.keys()))

            tweet = data.get("tweet", {})
            if not tweet:
                logger.info("响应中无推文数据。完整响应: %s", str(data)[:500])
                return CrawlResult(success=False, error="响应中无推文数据")

            logger.info(
                "推文: text=%s, author=%s, media_keys=%s",
                (tweet.get("text", ""))[:100],
                tweet.get("author", {}).get("screen_name", "?"),
                list(tweet.get("media", {}).keys()) if tweet.get("media") else "none",
            )

            # 提取媒体（仅图片）
            image_urls: list[str] = []
            media = tweet.get("media", {})
            photos = media.get("photos", [])
            logger.info("找到 %d 张图片", len(photos))

            for i, photo in enumerate(photos):
                url_orig = photo.get("url", "")
                logger.info("  图片 %d: url=%s", i, url_orig[:100] if url_orig else "(空)")
                if url_orig:
                    image_urls.append(url_orig)

            if not image_urls:
                # 记录所有媒体信息用于调试
                logger.info("未找到图片。完整媒体对象: %s", str(media)[:500])
                return CrawlResult(
                    success=False,
                    error="推文不包含图片",
                )

            # 作者信息
            author_info = tweet.get("author", {})
            author_name = author_info.get("name", "")
            author_screen = author_info.get("screen_name", user)

            # 可能为 NSFW
            is_nsfw = tweet.get("possibly_sensitive", False)

            logger.info(
                "Twitter 抓取成功: pid=%s, author=%s, images=%d, nsfw=%s",
                tweet_id, author_screen, len(image_urls), is_nsfw,
            )

            return CrawlResult(
                success=True,
                platform="twitter",
                pid=tweet_id,
                title=tweet.get("text", "")[:200],
                author=author_name,
                author_id=author_screen,
                source_url=f"https://x.com/{author_screen}/status/{tweet_id}",
                image_urls=image_urls,
                is_nsfw=is_nsfw,
                raw_info=tweet,
            )
