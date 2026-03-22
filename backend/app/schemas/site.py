from datetime import datetime

from pydantic import BaseModel


class FriendLinkResponse(BaseModel):
    id: int
    name: str
    url: str
    description: str
    avatar_url: str
    sort_order: int
    enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class FriendLinkCreate(BaseModel):
    name: str
    url: str
    description: str = ""
    avatar_url: str = ""
    sort_order: int = 100
    enabled: bool = True


class FriendLinkUpdate(BaseModel):
    name: str | None = None
    url: str | None = None
    description: str | None = None
    avatar_url: str | None = None
    sort_order: int | None = None
    enabled: bool | None = None
