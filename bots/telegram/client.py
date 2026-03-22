"""与 Hyacine Gallery 后端 API 通信的 HTTP 客户端。"""

from __future__ import annotations

from dataclasses import dataclass, field

import httpx


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

    async def import_artwork(self, url: str, tags: list[str] | None = None) -> ArtworkData:
        """调用后端导入接口：抓取 URL -> 创建作品。"""
        payload: dict[str, object] = {"url": url}
        if tags:
            payload["tags"] = tags
        resp = await self.http.post("/api/admin/artworks/import", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return ArtworkData.from_response(data["artwork"])

    # --- Bot 管理 API ---

    async def resolve_channel(self, artwork_id: int, platform: str = "telegram") -> ChannelData | None:
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

    async def get_bot_settings(self) -> dict[str, str]:
        """从后端获取所有 bot 设置。"""
        resp = await self.http.get("/api/admin/bot/settings")
        resp.raise_for_status()
        return {s["key"]: s["value"] for s in resp.json()}

    async def download_image(self, url: str) -> bytes:
        """下载图片字节（兼容本地存储 URL 和 S3 公开 URL）。"""
        resp = await self.http.get(url)
        resp.raise_for_status()
        return resp.content

    async def close(self) -> None:
        await self.http.aclose()
