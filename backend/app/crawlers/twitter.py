"""Twitter/X crawler using fxtwitter.com API (no auth required)."""

from __future__ import annotations

import re

import httpx

from app.crawlers.base import BaseCrawler, CrawlResult

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

    async def fetch(self, url: str) -> CrawlResult:
        info = _extract_info(url)
        if not info:
            return CrawlResult(success=False, error="Cannot extract tweet info")

        user, tweet_id = info

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(_FX_API.format(user=user, tweet_id=tweet_id))
            if resp.status_code != 200:
                return CrawlResult(
                    success=False,
                    error=f"fxtwitter API returned {resp.status_code}",
                )

            data = resp.json()
            tweet = data.get("tweet", {})
            if not tweet:
                return CrawlResult(success=False, error="No tweet data in response")

            # Extract media (photos only)
            image_urls: list[str] = []
            media = tweet.get("media", {})
            photos = media.get("photos", [])
            for photo in photos:
                url_orig = photo.get("url", "")
                if url_orig:
                    image_urls.append(url_orig)

            if not image_urls:
                return CrawlResult(
                    success=False,
                    error="Tweet contains no images",
                )

            # Author info
            author_info = tweet.get("author", {})
            author_name = author_info.get("name", "")
            author_screen = author_info.get("screen_name", user)

            # Possibly NSFW
            is_nsfw = tweet.get("possibly_sensitive", False)

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
