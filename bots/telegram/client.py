"""与 Hyacine Gallery 后端 API 通信的 HTTP 客户端。"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)


@dataclass
class ImageData:
    id: int
    page_index: int
    url_original: str
    url_thumb: str
    url_raw: str = ""
    width: int = 0
    height: int = 0


@dataclass
class TagData:
    id: int
    name: str
    type: str = "general"


@dataclass
class ArtworkData:
    id: int
    platform: str
    pid: str
    title: str
    title_zh: str
    author: str
    source_url: str
    is_nsfw: bool
    is_ai: bool
    images: list[ImageData] = field(default_factory=list)
    tags: list[TagData] = field(default_factory=list)

    @classmethod
    def from_response(cls, data: dict) -> ArtworkData:  # type: ignore[type-arg]
        images = [
            ImageData(
                id=img["id"],
                page_index=img["page_index"],
                url_original=img["url_original"],
                url_thumb=img["url_thumb"],
                url_raw=img.get("url_raw", ""),
                width=img.get("width", 0),
                height=img.get("height", 0),
            )
            for img in data.get("images", [])
        ]
        tags = [
            TagData(id=t["id"], name=t["name"], type=t.get("type", "general"))
            for t in data.get("tags", [])
        ]
        return cls(
            id=data["id"],
            platform=data["platform"],
            pid=data["pid"],
            title=data["title"],
            title_zh=data.get("title_zh", ""),
            author=data["author"],
            source_url=data["source_url"],
            is_nsfw=data["is_nsfw"],
            is_ai=data["is_ai"],
            images=images,
            tags=tags,
        )

    @property
    def tag_names(self) -> list[str]:
        return [t.name for t in self.tags]

    @property
    def image_urls(self) -> list[str]:
        return [img.url_original for img in sorted(self.images, key=lambda i: i.page_index)]

    @property
    def raw_image_urls(self) -> list[str]:
        """返回各页的 raw 原始文件 URL，空串表示该页无 raw 文件（已过期或未存储）。"""
        return [img.url_raw for img in sorted(self.images, key=lambda i: i.page_index)]


@dataclass
class SimilarArtwork:
    artwork_id: int
    distance: int
    platform: str
    pid: str
    title: str
    thumb_url: str

    @classmethod
    def from_response(cls, data: dict) -> SimilarArtwork:
        return cls(
            artwork_id=data["artwork_id"],
            distance=data["distance"],
            platform=data["platform"],
            pid=data["pid"],
            title=data.get("title", ""),
            thumb_url=data.get("thumb_url", ""),
        )


@dataclass
class ReverseSearchResult:
    source_url: str
    similarity: float
    platform: str
    title: str
    author: str
    thumb_url: str
    provider: str

    @classmethod
    def from_response(cls, data: dict) -> ReverseSearchResult:
        return cls(
            source_url=data["source_url"],
            similarity=data["similarity"],
            platform=data["platform"],
            title=data.get("title", ""),
            author=data.get("author", ""),
            thumb_url=data.get("thumb_url", ""),
            provider=data.get("provider", ""),
        )


@dataclass
class QueueItem:
    id: int
    artwork_id: int
    platform: str
    channel_id: str
    priority: int
    status: str
    added_by: str

    @classmethod
    def from_response(cls, data: dict) -> QueueItem:  # type: ignore[type-arg]
        return cls(
            id=data["id"],
            artwork_id=data["artwork_id"],
            platform=data["platform"],
            channel_id=data.get("channel_id", ""),
            priority=data["priority"],
            status=data["status"],
            added_by=data.get("added_by", ""),
        )


@dataclass
class ChannelData:
    id: int
    platform: str
    channel_id: str
    name: str
    is_default: bool
    priority: int
    conditions: dict  # type: ignore[type-arg]
    enabled: bool

    @classmethod
    def from_response(cls, data: dict) -> ChannelData:  # type: ignore[type-arg]
        return cls(
            id=data["id"],
            platform=data["platform"],
            channel_id=data["channel_id"],
            name=data["name"],
            is_default=data["is_default"],
            priority=data["priority"],
            conditions=data.get("conditions", {}),
            enabled=data["enabled"],
        )


class GalleryClient:
    def __init__(self, base_url: str, admin_token: str) -> None:
        self.http = httpx.AsyncClient(
            base_url=base_url,
            headers={"X-Admin-Token": admin_token},
            timeout=httpx.Timeout(connect=10.0, read=300.0, write=30.0, pool=10.0),
        )

    async def get_artwork(self, artwork_id: int) -> ArtworkData | None:
        resp = await self.http.get(f"/api/artworks/{artwork_id}")
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return ArtworkData.from_response(resp.json())

    async def get_random(self) -> ArtworkData | None:
        resp = await self.http.get("/api/artworks/random")
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return ArtworkData.from_response(resp.json())

    async def create_artwork(
        self,
        *,
        platform: str,
        pid: str,
        title: str = "",
        author: str = "",
        source_url: str = "",
        image_urls: list[str] | None = None,
        tags: list[str] | None = None,
        is_nsfw: bool = False,
        is_ai: bool = False,
    ) -> ArtworkData:
        payload = {
            "platform": platform,
            "pid": pid,
            "title": title,
            "author": author,
            "source_url": source_url,
            "image_urls": image_urls or [],
            "tags": tags or [],
            "is_nsfw": is_nsfw,
            "is_ai": is_ai,
        }
        resp = await self.http.post("/api/admin/artworks", json=payload)
        resp.raise_for_status()
        return ArtworkData.from_response(resp.json())

    async def search_artworks(
        self,
        *,
        q: str | None = None,
        tag: str | None = None,
        platform: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[ArtworkData], int]:
        params: dict[str, str | int] = {"page": page, "page_size": page_size}
        if q:
            params["q"] = q
        if tag:
            params["tag"] = tag
        if platform:
            params["platform"] = platform
        resp = await self.http.get("/api/artworks", params=params)
        resp.raise_for_status()
        data = resp.json()
        artworks = [ArtworkData.from_response(a) for a in data["data"]]
        return artworks, data["total"]

    async def semantic_search(self, query: str, top_k: int = 5) -> list[tuple[ArtworkData, float]]:
        """语义搜索，返回 (artwork, score) 列表。"""
        resp = await self.http.get("/api/artworks/search", params={"q": query, "top_k": top_k})
        resp.raise_for_status()
        data = resp.json()
        return [
            (ArtworkData.from_response(r["artwork"]), r["score"]) for r in data.get("results", [])
        ]

    async def search_by_image(self, image_data: bytes, threshold: int = 10) -> list[SimilarArtwork]:
        """上传图片到后端 pHash 搜索端点。"""
        resp = await self.http.post(
            "/api/admin/artworks/search-by-image",
            files={"file": ("search.jpg", image_data, "image/jpeg")},
            data={"threshold": str(threshold)},
        )
        resp.raise_for_status()
        return [SimilarArtwork.from_response(r) for r in resp.json()]

    async def reverse_search_image(
        self, image_data: bytes, min_similarity: float = 70.0
    ) -> list[ReverseSearchResult]:
        """上传图片到后端外部逆向搜索端点。"""
        resp = await self.http.post(
            "/api/admin/artworks/reverse-search",
            files={"file": ("search.jpg", image_data, "image/jpeg")},
            data={"min_similarity": str(min_similarity)},
        )
        resp.raise_for_status()
        return [ReverseSearchResult.from_response(r) for r in resp.json()]

    async def import_artwork(self, url: str, tags: list[str] | None = None) -> ArtworkData:
        """调用后端导入接口：抓取 URL -> 创建作品。"""
        payload: dict[str, object] = {"url": url}
        if tags:
            payload["tags"] = tags
        resp = await self.http.post("/api/admin/artworks/import", json=payload)
        if resp.status_code != 200:
            logger.error(
                "导入请求失败: status=%s url=%s body=%s",
                resp.status_code,
                url,
                resp.text[:500],
            )
        resp.raise_for_status()
        data = resp.json()
        return ArtworkData.from_response(data["artwork"])

    # --- Bot 管理 API ---

    async def resolve_channel(
        self, artwork_id: int, platform: str = "telegram"
    ) -> ChannelData | None:
        """向后端查询该作品应发布到哪个频道。"""
        resp = await self.http.post(
            "/api/admin/bot/channels/resolve",
            json={"artwork_id": artwork_id, "platform": platform},
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json()
        if data is None:
            return None
        return ChannelData.from_response(data)

    async def create_post_log(
        self,
        *,
        artwork_id: int,
        bot_platform: str = "telegram",
        channel_id: str,
        message_id: str = "",
        message_link: str = "",
        posted_by: str = "",
    ) -> dict:  # type: ignore[type-arg]
        resp = await self.http.post(
            "/api/admin/bot/post-logs",
            json={
                "artwork_id": artwork_id,
                "bot_platform": bot_platform,
                "channel_id": channel_id,
                "message_id": message_id,
                "message_link": message_link,
                "posted_by": posted_by,
            },
        )
        resp.raise_for_status()
        return resp.json()

    # --- 发布队列 API ---

    async def pop_queue_item(self, platform: str = "telegram") -> QueueItem | None:
        """取出下一条 pending 队列条目并标记为 processing。"""
        resp = await self.http.post("/api/admin/bot/queue/pop", params={"platform": platform})
        if resp.status_code == 200:
            data = resp.json()
            if data is None:
                return None
            return QueueItem.from_response(data)
        return None

    async def mark_queue_done(self, item_id: int) -> None:
        resp = await self.http.post(f"/api/admin/bot/queue/{item_id}/done")
        resp.raise_for_status()

    async def mark_queue_failed(self, item_id: int, error: str = "") -> None:
        await self.http.post(f"/api/admin/bot/queue/{item_id}/failed", params={"error": error})

    async def get_today_post_count(self, platform: str = "telegram") -> int:
        resp = await self.http.get(
            "/api/admin/bot/post-logs/today-count", params={"platform": platform}
        )
        if resp.status_code == 200:
            return int(resp.json().get("count", 0))
        return 0

    async def check_admin(self, tg_user_id: int) -> bool:
        """查询后端 users 表，判断指定 Telegram 用户是否有管理员权限。"""
        resp = await self.http.get("/api/auth/check-admin", params={"tg_id": tg_user_id})
        if resp.status_code == 200:
            return bool(resp.json().get("is_admin", False))
        return False

    async def get_bot_settings(self) -> dict[str, str]:
        """从后端获取所有 bot 设置。"""
        resp = await self.http.get("/api/admin/bot/settings")
        resp.raise_for_status()
        return {s["key"]: s["value"] for s in resp.json()}

    async def update_bot_settings(self, settings: dict[str, str]) -> None:
        """批量更新 bot 设置到后端。"""
        resp = await self.http.put("/api/admin/bot/settings", json={"settings": settings})
        resp.raise_for_status()

    async def download_image(self, url: str) -> bytes:
        """下载图片字节（兼容本地存储 URL 和 S3 公开 URL）。"""
        resp = await self.http.get(url)
        resp.raise_for_status()
        return resp.content

    async def close(self) -> None:
        await self.http.aclose()
