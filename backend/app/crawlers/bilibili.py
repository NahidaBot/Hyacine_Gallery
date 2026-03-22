"""BiliBili 动态爬虫，使用公开 Web API 抓取图文动态。"""

from __future__ import annotations

import logging
import re

import httpx

from app.crawlers.base import BaseCrawler, CrawlResult

logger = logging.getLogger(__name__)

# 匹配:
#   https://t.bilibili.com/1234567890
#   https://www.bilibili.com/opus/1234567890
#   https://bilibili.com/opus/1234567890
_PATTERN = re.compile(r"(?:https?://)?(?:www\.)?(?:t\.bilibili\.com|bilibili\.com/opus)/(\d+)")

_API_URL = "https://api.bilibili.com/x/polymer/web-dynamic/v1/detail?id={dynamic_id}"

# 从正文中提取 #标签# 格式的标签
_TAG_RE = re.compile(r"#([^#]+)#")


class BiliBiliCrawler(BaseCrawler):
    def match(self, url: str) -> bool:
        return _PATTERN.search(url) is not None

    def extract_identity(self, url: str) -> tuple[str, str] | None:
        m = _PATTERN.search(url)
        return ("bilibili", m.group(1)) if m else None

    async def fetch(self, url: str) -> CrawlResult:
        m = _PATTERN.search(url)
        if not m:
            return CrawlResult(success=False, error="无法提取 BiliBili 动态 ID")

        dynamic_id = m.group(1)
        logger.info("BiliBili 动态抓取: dynamic_id=%s", dynamic_id)

        api_url = _API_URL.format(dynamic_id=dynamic_id)
        headers = {
            "Referer": "https://www.bilibili.com/",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/146.0.0.0 Safari/537.36"
            ),
        }

        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            try:
                resp = await client.get(api_url)
            except httpx.HTTPError as e:
                logger.info("BiliBili 请求失败: %s", e)
                return CrawlResult(success=False, error=f"BiliBili 请求失败: {e}")

            if resp.status_code != 200:
                return CrawlResult(success=False, error=f"BiliBili API 返回 {resp.status_code}")

            data = resp.json()
            code = data.get("code", -1)
            if code != 0:
                return CrawlResult(
                    success=False,
                    error=f"BiliBili API 错误: {data.get('message', code)}",
                )

            item = data.get("data", {}).get("item")
            if not item:
                return CrawlResult(success=False, error="响应中无动态数据")

        modules = item.get("modules", {})

        # 提取图片
        draw = modules.get("module_dynamic", {}).get("major", {}).get("draw", {})
        draw_items: list[dict] = draw.get("items", [])

        image_urls: list[str] = []
        for img in draw_items:
            src = img.get("src", "")
            if src:
                # 确保使用 https
                if src.startswith("//"):
                    src = "https:" + src
                image_urls.append(src)

        if not image_urls:
            return CrawlResult(success=False, error="动态不包含图片")

        # 作者信息
        author_info = modules.get("module_author", {})
        author = author_info.get("name", "")
        author_mid = str(author_info.get("mid", ""))

        # 正文 / 标题
        desc = modules.get("module_dynamic", {}).get("desc", {})
        text = desc.get("text", "")
        # 取正文前 200 字符作为标题
        title = text[:200].split("\n")[0] if text else ""

        # 从正文提取标签
        tags: list[str] = _TAG_RE.findall(text)

        source_url = f"https://t.bilibili.com/{dynamic_id}"

        logger.info(
            "BiliBili 抓取成功: pid=%s, author=%s, images=%d, tags=%s",
            dynamic_id,
            author,
            len(image_urls),
            tags,
        )

        return CrawlResult(
            success=True,
            platform="bilibili",
            pid=dynamic_id,
            title=title,
            author=author,
            author_id=author_mid,
            source_url=source_url,
            image_urls=image_urls,
            tags=tags,
            raw_info=item,
        )
