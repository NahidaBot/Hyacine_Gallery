from datetime import datetime
from typing import Any

from pydantic import BaseModel

# --- Post Logs ---


class BotPostLogCreate(BaseModel):
    artwork_id: int
    bot_platform: str = "telegram"
    channel_id: str
    message_id: str = ""
    message_link: str = ""
    posted_by: str = ""


class BotPostLogResponse(BaseModel):
    id: int
    artwork_id: int
    bot_platform: str
    channel_id: str
    message_id: str
    message_link: str
    posted_by: str
    posted_at: datetime

    model_config = {"from_attributes": True}


class BotPostLogListResponse(BaseModel):
    data: list[BotPostLogResponse]
    total: int
    page: int
    page_size: int


# --- Bot Channels ---


class BotChannelCreate(BaseModel):
    platform: str = "telegram"
    channel_id: str
    name: str = ""
    is_default: bool = False
    priority: int = 0
    conditions: dict[str, Any] = {}
    enabled: bool = True


class BotChannelUpdate(BaseModel):
    channel_id: str | None = None
    name: str | None = None
    is_default: bool | None = None
    priority: int | None = None
    conditions: dict[str, Any] | None = None
    enabled: bool | None = None


class BotChannelResponse(BaseModel):
    id: int
    platform: str
    channel_id: str
    name: str
    is_default: bool
    priority: int
    conditions: dict[str, Any]
    enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class BotChannelResolveRequest(BaseModel):
    artwork_id: int
    platform: str = "telegram"


# --- Bot Settings ---


class BotSettingResponse(BaseModel):
    key: str
    value: str
    description: str

    model_config = {"from_attributes": True}


class BotSettingsUpdateRequest(BaseModel):
    settings: dict[str, str]


# --- 发布队列 ---


class QueueItemCreate(BaseModel):
    artwork_id: int
    platform: str = "telegram"
    channel_id: str = ""
    priority: int = 100


class QueueItemPriorityUpdate(BaseModel):
    priority: int


class QueueItemResponse(BaseModel):
    id: int
    artwork_id: int
    platform: str
    channel_id: str
    priority: int
    status: str
    added_by: str
    error: str
    created_at: datetime
    processed_at: datetime | None = None

    model_config = {"from_attributes": True}


class QueueListResponse(BaseModel):
    data: list[QueueItemResponse]
    total: int
    page: int
    page_size: int


class NextTimesResponse(BaseModel):
    times: list[datetime]
    interval_minutes: int
    pending_count: int
