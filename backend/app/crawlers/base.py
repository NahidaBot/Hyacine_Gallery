from abc import ABC, abstractmethod
from dataclasses import dataclass, field


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
