import json

from fastapi import APIRouter, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import AdminDep, DBDep
from app.schemas.bot import (
    BotChannelCreate,
    BotChannelResolveRequest,
    BotChannelResponse,
    BotChannelUpdate,
    BotPostLogCreate,
    BotPostLogListResponse,
    BotPostLogResponse,
    BotSettingResponse,
    BotSettingsUpdateRequest,
)
from app.services import artwork_service, bot_service

router = APIRouter(dependencies=[AdminDep])


# --- 发布日志 ---


@router.post("/post-logs", response_model=BotPostLogResponse)
async def create_post_log(
    data: BotPostLogCreate, db: AsyncSession = DBDep
) -> BotPostLogResponse:
    log = await bot_service.create_post_log(db, data)
    return BotPostLogResponse.model_validate(log)


@router.get("/post-logs", response_model=BotPostLogListResponse)
async def list_post_logs(
    artwork_id: int | None = None,
    channel_id: str | None = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = DBDep,
) -> BotPostLogListResponse:
    logs, total = await bot_service.get_post_logs(
        db, artwork_id=artwork_id, channel_id=channel_id, page=page, page_size=page_size
    )
    return BotPostLogListResponse(
        data=[BotPostLogResponse.model_validate(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
    )


# --- 机器人频道 ---


@router.get("/channels", response_model=list[BotChannelResponse])
async def list_channels(
    platform: str = "telegram", db: AsyncSession = DBDep
) -> list[BotChannelResponse]:
    channels = await bot_service.get_channels(db, platform)
    return [_channel_to_response(ch) for ch in channels]


@router.post("/channels", response_model=BotChannelResponse)
async def create_channel(
    data: BotChannelCreate, db: AsyncSession = DBDep
) -> BotChannelResponse:
    channel = await bot_service.create_channel(db, data)
    return _channel_to_response(channel)


@router.put("/channels/{channel_id}", response_model=BotChannelResponse)
async def update_channel(
    channel_id: int, data: BotChannelUpdate, db: AsyncSession = DBDep
) -> BotChannelResponse:
    channel = await bot_service.update_channel(db, channel_id, data)
    if not channel:
        raise HTTPException(404, "频道不存在")
    return _channel_to_response(channel)


@router.delete("/channels/{channel_id}")
async def delete_channel(
    channel_id: int, db: AsyncSession = DBDep
) -> dict[str, str]:
    deleted = await bot_service.delete_channel(db, channel_id)
    if not deleted:
        raise HTTPException(404, "频道不存在")
    return {"status": "deleted"}


@router.post("/channels/resolve", response_model=BotChannelResponse | None)
async def resolve_channel(
    data: BotChannelResolveRequest, db: AsyncSession = DBDep
) -> BotChannelResponse | None:
    artwork = await artwork_service.get_artwork_by_id(db, data.artwork_id)
    if not artwork:
        raise HTTPException(404, "作品不存在")
    channel = await bot_service.resolve_channel(db, artwork, data.platform)
    if not channel:
        return None
    return _channel_to_response(channel)


# --- 机器人设置 ---


@router.get("/settings", response_model=list[BotSettingResponse])
async def list_settings(db: AsyncSession = DBDep) -> list[BotSettingResponse]:
    settings = await bot_service.get_settings_list(db)
    return [BotSettingResponse.model_validate(s) for s in settings]


@router.put("/settings")
async def update_settings(
    data: BotSettingsUpdateRequest, db: AsyncSession = DBDep
) -> dict[str, str]:
    await bot_service.set_settings(db, data.settings)
    return {"status": "updated"}


@router.get("/settings/{key}", response_model=BotSettingResponse)
async def get_setting(key: str, db: AsyncSession = DBDep) -> BotSettingResponse:
    settings = await bot_service.get_settings_list(db)
    for s in settings:
        if s.key == key:
            return BotSettingResponse.model_validate(s)
    raise HTTPException(404, "设置不存在")


def _channel_to_response(channel) -> BotChannelResponse:  # type: ignore[no-untyped-def]
    conditions = channel.conditions
    if isinstance(conditions, str):
        conditions = json.loads(conditions) if conditions else {}
    return BotChannelResponse(
        id=channel.id,
        platform=channel.platform,
        channel_id=channel.channel_id,
        name=channel.name,
        is_default=channel.is_default,
        priority=channel.priority,
        conditions=conditions,
        enabled=channel.enabled,
        created_at=channel.created_at,
    )
