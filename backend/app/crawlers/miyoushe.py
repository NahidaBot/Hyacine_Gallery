"""MiYouShe / HoYoLAB crawler via public Web API."""

from __future__ import annotations

import logging
import re

import httpx

from app.crawlers.base import BaseCrawler, CrawlResult

logger = logging.getLogger(__name__)

# Matches:
#   https://miyoushe.com/ys/article/54064752
#   https://www.miyoushe.com/sr/article/54064752
#   https://bbs.mihoyo.com/ys/article/54064752
#   https://hoyolab.com/article/30083385
#   https://www.hoyolab.com/article/30083385
_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.)?(?:miyoushe|hoyolab|bbs\.mihoyo)\.com/"
    r"(?:[a-z]+/)?article/(\d+)"
)

_API_CN = "https://bbs-api.miyoushe.com/post/wapi/getPostFull?post_id={post_id}"
_API_GLOBAL = "https://bbs-api-os.hoyolab.com/community/post/wapi/getPostFull?post_id={post_id}"

_GAME_MAP: dict[int, tuple[str, str]] = {
    1: ("崩坏3", "bh3"),
    2: ("原神", "ys"),
    3: ("崩坏学园2", "bh2"),
    4: ("未定事件簿", "wd"),
    5: ("大别野", "dby"),
    6: ("星铁", "sr"),
    7: ("大别野", "dby"),
    8: ("绝区零", "zzz"),
}


class MiYouSheCrawler(BaseCrawler):
    def match(self, url: str) -> bool:
        return _PATTERN.search(url) is not None

    async def fetch(self, url: str) -> CrawlResult:
        m = _PATTERN.search(url)
        if not m:
            return CrawlResult(success=False, error="Cannot extract MiYouShe post ID")

        post_id = m.group(1)
        is_global = "hoyolab" in url
        logger.info("MiYouShe crawl: post_id=%s, global=%s", post_id, is_global)

        api_url = _API_GLOBAL.format(post_id=post_id) if is_global else _API_CN.format(post_id=post_id)
        referer = "https://www.hoyolab.com/" if is_global else "https://www.miyoushe.com/"

        headers = {
            "Referer": referer,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
            "X-Rpc-Language": "zh-cn",
        }

        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            try:
                resp = await client.get(api_url)
            except httpx.HTTPError as e:
                logger.info("MiYouShe request failed: %s", e)
                return CrawlResult(success=False, error=f"MiYouShe request failed: {e}")

            logger.info("MiYouShe response: status=%d, length=%d", resp.status_code, len(resp.content))

            if resp.status_code != 200:
                logger.info("MiYouShe error body: %s", resp.text[:500])
                return CrawlResult(
                    success=False,
                    error=f"MiYouShe API returned {resp.status_code}",
                )

            data = resp.json()
            retcode = data.get("retcode", -1)
            if retcode != 0:
                logger.info("MiYouShe API error: retcode=%s, message=%s", retcode, data.get("message", ""))
                return CrawlResult(success=False, error=f"MiYouShe API error: {data.get('message', retcode)}")

            post = data.get("data", {}).get("post")
            if not post:
                logger.info("No post data in response")
                return CrawlResult(success=False, error="No post data in response")

        # Extract images
        image_list: list[dict] = post.get("image_list", [])
        logger.info("Found %d images", len(image_list))

        image_urls: list[str] = []
        for i, img in enumerate(image_list):
            img_url = img.get("url", "")
            if img_url:
                image_urls.append(img_url)
                logger.info("  Image %d: %dx%d, %s", i, img.get("width", 0), img.get("height", 0), img_url[:80])

        if not image_urls:
            return CrawlResult(success=False, error="Post contains no images")

        # Post metadata
        post_meta = post.get("post", {})
        user_info = post.get("user", {})
        title = post_meta.get("subject", "")
        author = user_info.get("nickname", "")
        author_uid = str(user_info.get("uid", ""))

        # Build source URL
        game_id = post_meta.get("game_id", 0)
        game_name, url_path = _GAME_MAP.get(game_id, ("", "ys"))

        if is_global:
            source_url = f"https://www.hoyolab.com/article/{post_id}"
        else:
            source_url = f"https://www.miyoushe.com/{url_path}/article/{post_id}"

        # Tags from topics
        tags: list[str] = []
        for topic in post.get("topics", []):
            name = topic.get("name", "")
            if name:
                tags.append(name)
        if game_name:
            tags.append(game_name)

        logger.info(
            "MiYouShe crawl success: pid=%s, title=%s, author=%s, images=%d, tags=%s",
            post_id, title[:50], author, len(image_urls), tags,
        )

        return CrawlResult(
            success=True,
            platform="miyoushe",
            pid=post_id,
            title=title,
            author=author,
            author_id=author_uid,
            source_url=source_url,
            image_urls=image_urls,
            tags=tags,
            raw_info=post,
        )
