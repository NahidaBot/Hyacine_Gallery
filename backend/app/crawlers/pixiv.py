"""Pixiv 作品爬虫，使用公开 Ajax API。"""

from __future__ import annotations

import re

import httpx

from app.crawlers.base import BaseCrawler, CrawlResult

_PIXIV_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.)?pixiv\.net/(?:en/)?artworks/(\d+)"
)
_PHIXIV_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.)?phixiv\.net/(?:en/)?artworks/(\d+)"
)

_AJAX_URL = "https://www.pixiv.net/ajax/illust/{pid}?lang=en"
_PAGES_URL = "https://www.pixiv.net/ajax/illust/{pid}/pages?lang=en"

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.pixiv.net/",
}


def _extract_pid(url: str) -> str | None:
    for pattern in (_PIXIV_PATTERN, _PHIXIV_PATTERN):
        m = pattern.search(url)
        if m:
            return m.group(1)
    return None


class PixivCrawler(BaseCrawler):
    def match(self, url: str) -> bool:
        return _extract_pid(url) is not None

    async def fetch(self, url: str) -> CrawlResult:
        pid = _extract_pid(url)
        if not pid:
            return CrawlResult(success=False, error="无法提取 Pixiv 作品 ID")

        async with httpx.AsyncClient(headers=_HEADERS, timeout=30.0) as client:
            # 获取作品详情
            resp = await client.get(_AJAX_URL.format(pid=pid))
            if resp.status_code != 200:
                return CrawlResult(
                    success=False,
                    error=f"Pixiv API 返回 {resp.status_code}",
                )
            data = resp.json()
            if data.get("error"):
                return CrawlResult(
                    success=False,
                    error=data.get("message", "Pixiv API 错误"),
                )

            body = data["body"]

            # 获取图片分页
            pages_resp = await client.get(_PAGES_URL.format(pid=pid))
            pages_resp.raise_for_status()
            pages_data = pages_resp.json()
            image_urls = [
                page["urls"]["original"]
                for page in pages_data.get("body", [])
            ]

            # 提取标签
            tags: list[str] = []
            for tag_info in body.get("tags", {}).get("tags", []):
                tag_name = tag_info.get("tag", "")
                if tag_name:
                    tags.append(tag_name)
                # 如果有英文翻译也一并添加
                translation = tag_info.get("translation", {}).get("en")
                if translation and translation != tag_name:
                    tags.append(translation)

            # 首页尺寸
            width = body.get("width", 0)
            height = body.get("height", 0)

            # R-18 检查
            is_nsfw = body.get("xRestrict", 0) > 0

            # AI 检查 (Pixiv aiType: 0=未指定, 1=非AI, 2=AI)
            is_ai = body.get("aiType", 0) == 2

            return CrawlResult(
                success=True,
                platform="pixiv",
                pid=pid,
                title=body.get("title", ""),
                author=body.get("userName", ""),
                author_id=str(body.get("userId", "")),
                source_url=f"https://www.pixiv.net/artworks/{pid}",
                image_urls=image_urls,
                tags=tags,
                width=width,
                height=height,
                is_nsfw=is_nsfw,
                is_ai=is_ai,
                raw_info=body,
            )
