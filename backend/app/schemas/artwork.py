from datetime import datetime

from pydantic import BaseModel


class ArtworkImageResponse(BaseModel):
    id: int
    page_index: int
    url_original: str
    url_thumb: str
    width: int
    height: int
    file_size: int
    file_name: str
    storage_path: str

    model_config = {"from_attributes": True}


class TagBrief(BaseModel):
    id: int
    name: str
    type: str

    model_config = {"from_attributes": True}


class ArtworkResponse(BaseModel):
    id: int
    platform: str
    pid: str
    title: str
    author: str
    author_id: str
    source_url: str
    page_count: int
    is_nsfw: bool
    is_ai: bool
    images: list[ArtworkImageResponse]
    tags: list[TagBrief]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ArtworkListResponse(BaseModel):
    data: list[ArtworkResponse]
    total: int
    page: int
    page_size: int


class ArtworkCreate(BaseModel):
    platform: str
    pid: str
    title: str = ""
    author: str = ""
    author_id: str = ""
    source_url: str = ""
    page_count: int = 1
    is_nsfw: bool = False
    is_ai: bool = False
    image_urls: list[str] = []
    tags: list[str] = []


class ArtworkUpdate(BaseModel):
    title: str | None = None
    author: str | None = None
    author_id: str | None = None
    source_url: str | None = None
    is_nsfw: bool | None = None
    is_ai: bool | None = None
    tags: list[str] | None = None


class ArtworkImportRequest(BaseModel):
    url: str
    tags: list[str] = []
