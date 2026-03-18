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
