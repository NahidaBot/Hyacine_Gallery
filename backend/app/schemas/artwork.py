from datetime import datetime

from pydantic import BaseModel


class ArtworkBase(BaseModel):
    platform: str
    pid: str
    title: str = ""
    author: str = ""
    author_id: str = ""
    source_url: str = ""
    page_count: int = 1
    width: int = 0
    height: int = 0
    is_nsfw: bool = False
    is_ai: bool = False


class ArtworkCreate(ArtworkBase):
    tags: list[str] = []


class ArtworkImportRequest(BaseModel):
    url: str
    tags: list[str] = []


class ArtworkResponse(ArtworkBase):
    id: int
    images_json: str = "[]"
    tags: list[str] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ArtworkListResponse(BaseModel):
    data: list[ArtworkResponse]
    total: int
    page: int
    page_size: int


class ImportResponse(BaseModel):
    success: bool
    message: str
    artwork: ArtworkResponse | None = None
