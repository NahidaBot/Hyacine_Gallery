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
    """Base class for platform-specific crawlers."""

    @abstractmethod
    def match(self, url: str) -> bool:
        """Return True if this crawler can handle the given URL."""
        ...

    @abstractmethod
    async def fetch(self, url: str) -> CrawlResult:
        """Fetch artwork metadata and image URLs from the given URL."""
        ...
