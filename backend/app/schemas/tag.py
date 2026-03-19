from datetime import datetime

from pydantic import BaseModel


class TagCreate(BaseModel):
    name: str
    type: str = "general"
    alias_of_id: int | None = None


class TagUpdate(BaseModel):
    name: str | None = None
    type: str | None = None
    alias_of_id: int | None = None


class TagResponse(BaseModel):
    id: int
    name: str
    type: str
    alias_of_id: int | None
    created_at: datetime
    artwork_count: int = 0

    model_config = {"from_attributes": True}


class TagListResponse(BaseModel):
    data: list[TagResponse]
    total: int


# ── Tag Types ──


class TagTypeCreate(BaseModel):
    name: str
    label: str = ""
    color: str = ""
    sort_order: int = 0


class TagTypeUpdate(BaseModel):
    name: str | None = None
    label: str | None = None
    color: str | None = None
    sort_order: int | None = None


class TagTypeResponse(BaseModel):
    id: int
    name: str
    label: str
    color: str
    sort_order: int
    tag_count: int = 0

    model_config = {"from_attributes": True}
