"""HTTP client for communicating with the Hyacine Gallery backend API."""

from __future__ import annotations

from dataclasses import dataclass, field

import httpx


@dataclass
class ImageData:
    id: int
    page_index: int
    url_original: str
    url_thumb: str
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


class GalleryClient:
    def __init__(self, base_url: str, admin_token: str) -> None:
        self.http = httpx.AsyncClient(
            base_url=base_url,
            headers={"X-Admin-Token": admin_token},
            timeout=60.0,
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

    async def close(self) -> None:
        await self.http.aclose()
