import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_RETRYABLE_ERRORS = (
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.WriteTimeout,
    httpx.ConnectError,
    httpx.ReadError,
)


async def fetch_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    max_retries: int = 5,
    **kwargs: Any,
) -> httpx.Response:
    """带指数退避的 HTTP 请求。短超时快速失败，自动重试网络错误。

    成功返回 Response（不检查状态码），网络错误耗尽重试次数后抛出最后的异常。
    """
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            return await client.request(method, url, **kwargs)
        except _RETRYABLE_ERRORS as e:
            last_exc = e
            if attempt == max_retries - 1:
                break
            wait = min(2**attempt, 30)
            logger.warning(
                "请求失败（第 %d 次），%.0fs 后重试: %s %s — %s",
                attempt + 1,
                wait,
                method,
                url[:80],
                e,
            )
            await asyncio.sleep(wait)
    raise last_exc  # type: ignore[misc]


@dataclass
class CrawlResult:
    success: bool
    platform: str = ""
    pid: str = ""
    title: str = ""
    author: str = ""
    author_id: str = ""
    source_url: str = ""
    image_urls: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    width: int = 0
    height: int = 0
    is_nsfw: bool = False
    is_ai: bool = False
    raw_info: dict = field(default_factory=dict)  # type: ignore[type-arg]
    error: str = ""


class BaseCrawler(ABC):
    """各平台爬虫的基类。"""

    @abstractmethod
    def match(self, url: str) -> bool:
        """判断当前爬虫是否能处理给定的 URL。"""
        ...

    @abstractmethod
    async def fetch(self, url: str) -> CrawlResult:
        """从给定 URL 抓取作品元数据和图片链接。"""
        ...

    def extract_identity(self, url: str) -> tuple[str, str] | None:
        """从 URL 直接提取 (platform, pid)，无需网络请求。
        子类若能从 URL 解析出唯一标识则重写此方法；
        无法静态提取的爬虫（如 gallery-dl）保持默认返回 None。
        """
        return None
