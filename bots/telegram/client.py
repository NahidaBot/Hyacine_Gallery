"""HTTP client for communicating with the Hyacine Gallery backend API."""

from dataclasses import dataclass

import httpx


@dataclass
class ArtworkData:
    id: int
    platform: str
    pid: str
    title: str
    author: str
    source_url: str
    images_json: str
    tags: list[str]
    is_nsfw: bool
    is_ai: bool


class GalleryClient:
    def __init__(self, base_url: str, admin_token: str) -> None:
        self.http = httpx.AsyncClient(
            base_url=base_url,
            headers={"X-Admin-Token": admin_token},
            timeout=60.0,
        )

    async def import_artwork(self, url: str, tags: list[str]) -> dict:  # type: ignore[type-arg]
        resp = await self.http.post("/api/admin/artworks", json={"url": url, "tags": tags})
        resp.raise_for_status()
        return resp.json()

    async def get_random(self) -> ArtworkData:
        resp = await self.http.get("/api/artworks/random")
        resp.raise_for_status()
        data = resp.json()
        return ArtworkData(
            id=data["id"],
            platform=data["platform"],
            pid=data["pid"],
            title=data["title"],
            author=data["author"],
            source_url=data["source_url"],
            images_json=data["images_json"],
            tags=data["tags"],
            is_nsfw=data["is_nsfw"],
            is_ai=data["is_ai"],
        )

    async def close(self) -> None:
        await self.http.aclose()
