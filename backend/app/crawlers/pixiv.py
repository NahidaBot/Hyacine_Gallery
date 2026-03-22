"""Pixiv 作品爬虫，使用公开 Ajax API。"""

from __future__ import annotations

import asyncio
import logging
import re

import httpx

logger = logging.getLogger(__name__)

from app.crawlers.base import BaseCrawler, CrawlResult

# 匹配 CJK 统一表意文字范围（用于中文优先 tag 策略）
_CHINESE_RE = re.compile(r"[一-龥]")

_PIXIV_PATTERN = re.compile(r"(?:https?://)?(?:www\.)?pixiv\.net/(?:en/)?artworks/(\d+)")
_PHIXIV_PATTERN = re.compile(r"(?:https?://)?(?:www\.)?phixiv\.net/(?:en/)?artworks/(\d+)")

_AJAX_URL = "https://www.pixiv.net/ajax/illust/{pid}?lang=zh"
_PAGES_URL = "https://www.pixiv.net/ajax/illust/{pid}/pages?lang=zh"

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.pixiv.net/",
    "sec-ch-ua": '"Chromium";v="136", "Google Chrome";v="136", "Not-A.Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
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

    def extract_identity(self, url: str) -> tuple[str, str] | None:
        pid = _extract_pid(url)
        return ("pixiv", pid) if pid else None

    async def fetch(self, url: str) -> CrawlResult:
        pid = _extract_pid(url)
        if not pid:
            return CrawlResult(success=False, error="无法提取 Pixiv 作品 ID")

        _RETRIES = 10
        async with httpx.AsyncClient(headers=_HEADERS, timeout=2.0) as client:
            # 获取作品详情（指数避让重试）
            resp = None
            for attempt in range(_RETRIES):
                try:
                    resp = await client.get(_AJAX_URL.format(pid=pid))
                    break
                except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError) as e:
                    if attempt == _RETRIES - 1:
                        return CrawlResult(
                            success=False, error=f"请求超时，已重试 {_RETRIES} 次: {e}"
                        )
                    wait = 2**attempt
                    logger.warning(
                        "Pixiv 请求失败（第 %d 次），%.0fs 后重试: %s", attempt + 1, wait, e
                    )
                    await asyncio.sleep(wait)

            assert resp is not None
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

            # 获取图片分页（同样重试）
            pages_resp = None
            for attempt in range(_RETRIES):
                try:
                    pages_resp = await client.get(_PAGES_URL.format(pid=pid))
                    pages_resp.raise_for_status()
                    break
                except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError) as e:
                    if attempt == _RETRIES - 1:
                        return CrawlResult(
                            success=False, error=f"获取分页超时，已重试 {_RETRIES} 次: {e}"
                        )
                    wait = 2**attempt
                    logger.warning(
                        "Pixiv 分页请求失败（第 %d 次），%.0fs 后重试: %s", attempt + 1, wait, e
                    )
                    await asyncio.sleep(wait)
            assert pages_resp is not None
            pages_data = pages_resp.json()
            image_urls = [page["urls"]["original"] for page in pages_data.get("body", [])]

            # 提取标签（中文优先策略）
            tags: list[str] = []
            for tag_info in body.get("tags", {}).get("tags", []):
                tag_raw: str = tag_info.get("tag", "")
                if not tag_raw or "users入り" in tag_raw:
                    continue
                trans: dict[str, str] = tag_info.get("translation") or {}
                translation_zh: str = trans.get("zh", "")
                translation_en: str = trans.get("en", "")

                if translation_zh and translation_zh != tag_raw:
                    # 有中文翻译，直接使用（如フラミンゴ → 火烈鸟）
                    chosen = translation_zh
                elif translation_en and translation_en != tag_raw and translation_en.isascii():
                    # 英文翻译是纯 ASCII：若原 tag 含中文则保留原 tag，否则用翻译
                    # （原神 不变为 Genshin Impact；フラミンゴ 无中文翻译时用 flamingo）
                    chosen = tag_raw if _CHINESE_RE.search(tag_raw) else translation_en
                else:
                    # 无翻译或翻译非 ASCII：使用原 tag
                    chosen = tag_raw
                tags.append(chosen)

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
