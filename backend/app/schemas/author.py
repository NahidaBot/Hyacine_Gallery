from datetime import datetime

from pydantic import BaseModel


class AuthorCreate(BaseModel):
    name: str
    platform: str
    platform_uid: str = ""
    canonical_id: int | None = None


class AuthorUpdate(BaseModel):
    name: str | None = None
    canonical_id: int | None = None


class AuthorResponse(BaseModel):
    id: int
    name: str
    platform: str
    platform_uid: str
    canonical_id: int | None
    created_at: datetime
    artwork_count: int = 0

    model_config = {"from_attributes": True}
