"""BiliBili 动态爬虫，使用公开 Web API 抓取图文动态。"""

from __future__ import annotations

import logging
import re
from typing import Any

import httpx

from app.crawlers.base import BaseCrawler, CrawlResult, fetch_with_retry

logger = logging.getLogger(__name__)

# 匹配:
#   https://t.bilibili.com/1234567890
#   https://www.bilibili.com/opus/1234567890
#   https://bilibili.com/opus/1234567890
_PATTERN = re.compile(r"(?:https?://)?(?:www\.)?(?:t\.bilibili\.com|bilibili\.com/opus)/(\d+)")

_API_URL = (
    "https://api.bilibili.com/x/polymer/web-dynamic/v1/detail"
    "?id={dynamic_id}"
    "&features=itemOpusStyle,opusBigCover,onlyfansVote,endFooterHidden,"
    "decorationCard,onlyfansAssetsV2,ugcDelete,onlyfansQaCard,editable,"
    "opusPrivateVisible,avatarAutoTheme,sunflowerStyle,cardsEnhance,"
    "eva3CardOpus,eva3CardVideo,eva3CardComment,eva3CardVote,eva3CardUser"
)

# 模拟 Chrome 浏览器请求头，降低被风控拦截的概率
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/136.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.bilibili.com/",
    "Origin": "https://www.bilibili.com",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Sec-Ch-Ua": '"Chromium";v="136", "Not.A/Brand";v="99", "Google Chrome";v="136"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
}

# 从正文中提取 #标签# 格式的标签
_TAG_RE = re.compile(r"#([^#]+)#")


def _ensure_https(url: str) -> str:
    """将 // 或 http:// 开头的 URL 统一为 https://。"""
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("http://"):
        return "https://" + url[7:]
    return url


class BiliBiliCrawler(BaseCrawler):
    def match(self, url: str) -> bool:
        return _PATTERN.search(url) is not None

    def extract_identity(self, url: str) -> tuple[str, str] | None:
        m = _PATTERN.search(url)
        return ("bilibili", m.group(1)) if m else None

    async def fetch(self, url: str) -> CrawlResult:
        m = _PATTERN.search(url)
        if not m:
            logger.debug("URL 不匹配 BiliBili 模式: %s", url)
            return CrawlResult(success=False, error="无法提取 BiliBili 动态 ID")

        dynamic_id = m.group(1)
        api_url = _API_URL.format(dynamic_id=dynamic_id)
        logger.info("BiliBili 动态抓取: dynamic_id=%s", dynamic_id)
        logger.debug("请求 URL: %s", api_url)
        logger.debug("请求 Headers: %s", _HEADERS)

        async with httpx.AsyncClient(timeout=5.0, headers=_HEADERS) as client:
            try:
                resp = await fetch_with_retry(client, "GET", api_url)
            except httpx.HTTPError as e:
                logger.info("BiliBili 请求失败（已重试）: %s", e)
                return CrawlResult(success=False, error=f"BiliBili 请求失败: {e}")

            logger.info("BiliBili API 响应: status=%d, dynamic_id=%s", resp.status_code, dynamic_id)
            logger.debug("响应 Headers: %s", dict(resp.headers))

            if resp.status_code != 200:
                body_preview = resp.text[:500]
                logger.debug("非 200 响应体: %s", body_preview)
                return CrawlResult(success=False, error=f"BiliBili API 返回 {resp.status_code}")

            data = resp.json()
            code = data.get("code", -1)
            if code != 0:
                logger.info("BiliBili API 业务错误: code=%d, message=%s", code, data.get("message"))
                logger.debug("完整响应: %s", data)
                return CrawlResult(
                    success=False,
                    error=f"BiliBili API 错误: {data.get('message', code)}",
                )

            item = data.get("data", {}).get("item")
            if not item:
                logger.info("BiliBili 响应中无动态数据: dynamic_id=%s", dynamic_id)
                logger.debug("data 字段内容: %s", data.get("data"))
                return CrawlResult(success=False, error="响应中无动态数据")

        modules = item.get("modules", {})
        logger.debug("动态类型: %s", item.get("type"))
        logger.debug("modules 可用键: %s", list(modules.keys()))

        dynamic_mod: dict[str, Any] = modules.get("module_dynamic") or {}
        major: dict[str, Any] = dynamic_mod.get("major") or {}
        major_type: str = major.get("type", "")
        logger.debug("module_dynamic 解析: major.type=%s", major_type)

        # 提取图片和正文 — 根据 major.type 走不同分支
        #   MAJOR_TYPE_OPUS:  features 含 itemOpusStyle 时返回, 图片在 opus.pics[].url
        #   MAJOR_TYPE_DRAW:  经典格式, 图片在 draw.items[].src
        image_urls: list[str] = []
        text: str = ""

        if major_type == "MAJOR_TYPE_OPUS":
            opus: dict[str, Any] = major.get("opus") or {}
            pics: list[dict[str, Any]] = opus.get("pics", [])
            logger.debug("opus 模式: pics=%d", len(pics))
            for pic in pics:
                src = pic.get("url", "")
                if src:
                    image_urls.append(_ensure_https(src))
            # opus 正文在 summary.text，标题在 opus.title
            summary: dict[str, Any] = opus.get("summary") or {}
            text = summary.get("text") or ""
            opus_title: str = opus.get("title") or ""
            if opus_title:
                text = f"{opus_title}\n{text}"
        else:
            # MAJOR_TYPE_DRAW 或其他格式
            draw: dict[str, Any] = major.get("draw") or {}
            draw_items: list[dict[str, Any]] = draw.get("items", [])
            logger.debug("draw 模式: items=%d", len(draw_items))
            for img in draw_items:
                src = img.get("src", "")
                if src:
                    image_urls.append(_ensure_https(src))
            # 经典格式正文在 desc.text
            desc: dict[str, Any] = dynamic_mod.get("desc") or {}
            text = desc.get("text") or ""

        if not image_urls:
            logger.info("BiliBili 动态无图片: dynamic_id=%s", dynamic_id)
            logger.debug("major 原始内容: %s", major)
            return CrawlResult(success=False, error="动态不包含图片")

        logger.debug("提取到图片 %d 张, 正文: %r", len(image_urls), text[:100])

        # 作者信息
        author_info = modules.get("module_author", {})
        author = author_info.get("name", "")
        author_mid = str(author_info.get("mid", ""))

        # 取正文前 200 字符的首行作为标题
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
        logger.debug(
            "详细结果: title=%r, author_mid=%s, image_urls=%s",
            title,
            author_mid,
            image_urls,
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
