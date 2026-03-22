from datetime import datetime

from pydantic import BaseModel


class ArtworkImageResponse(BaseModel):
    id: int
    page_index: int
    url_original: str
    url_thumb: str
    url_raw: str = ""
    raw_expires_at: datetime | None = None
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


class ArtworkSourceResponse(BaseModel):
    id: int
    platform: str
    pid: str
    source_url: str
    is_primary: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ArtworkResponse(BaseModel):
    id: int
    platform: str
    pid: str
    title: str
    title_zh: str
    author: str
    author_id: str
    source_url: str
    page_count: int
    is_nsfw: bool
    is_ai: bool
    images: list[ArtworkImageResponse]
    tags: list[TagBrief]
    sources: list[ArtworkSourceResponse] = []
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
    title_zh: str | None = None
    author: str | None = None
    author_id: str | None = None
    source_url: str | None = None
    is_nsfw: bool | None = None
    is_ai: bool | None = None
    tags: list[str] | None = None


class ArtworkImportRequest(BaseModel):
    url: str
    tags: list[str] = []
    auto_merge: bool = False
    add_to_queue: bool = False  # 导入成功后加入 bot 发布队列
    queue_priority: int = 50  # 队列优先级（50 较高，默认 100）


class ArtworkAddSourceRequest(BaseModel):
    url: str


class ArtworkMergeRequest(BaseModel):
    source_artwork_id: int


class SimilarArtworkInfo(BaseModel):
    artwork_id: int
    distance: int
    platform: str
    pid: str
    title: str
    thumb_url: str

    model_config = {"from_attributes": True}


class ImportResponse(BaseModel):
    """Extended import response that may include similar artwork candidates."""

    artwork: ArtworkResponse | None = None
    similar: list[SimilarArtworkInfo] = []
    merged: bool = False
    message: str = ""
    queued: bool = False  # 是否已加入 bot 发布队列


class SemanticSearchResult(BaseModel):
    artwork: ArtworkResponse
    score: float


class SemanticSearchResponse(BaseModel):
    results: list[SemanticSearchResult]
    query: str
