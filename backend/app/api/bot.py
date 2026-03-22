import json
from datetime import UTC, datetime, timedelta

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
    NextTimesResponse,
    QueueItemCreate,
    QueueItemPriorityUpdate,
    QueueItemResponse,
    QueueListResponse,
)
from app.services import artwork_service, bot_service, queue_service

router = APIRouter(dependencies=[AdminDep])


# --- 发布日志 ---


@router.post("/post-logs", response_model=BotPostLogResponse)
async def create_post_log(data: BotPostLogCreate, db: AsyncSession = DBDep) -> BotPostLogResponse:
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
async def create_channel(data: BotChannelCreate, db: AsyncSession = DBDep) -> BotChannelResponse:
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
async def delete_channel(channel_id: int, db: AsyncSession = DBDep) -> dict[str, str]:
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


# --- 发布队列 ---


@router.get("/queue", response_model=QueueListResponse)
async def list_queue(
    status: str | None = "pending",
    platform: str = "telegram",
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = DBDep,
) -> QueueListResponse:
    items, total = await queue_service.list_queue(
        db, status=status, platform=platform, page=page, page_size=page_size
    )
    return QueueListResponse(
        data=[QueueItemResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/queue", response_model=QueueItemResponse)
async def add_to_queue(data: QueueItemCreate, db: AsyncSession = DBDep) -> QueueItemResponse:
    artwork = await artwork_service.get_artwork_by_id(db, data.artwork_id)
    if not artwork:
        raise HTTPException(404, "作品不存在")
    item = await queue_service.add_to_queue(
        db,
        data.artwork_id,
        platform=data.platform,
        channel_id=data.channel_id,
        priority=data.priority,
        added_by="admin",
    )
    return QueueItemResponse.model_validate(item)


@router.delete("/queue/{item_id}")
async def delete_queue_item(item_id: int, db: AsyncSession = DBDep) -> dict[str, str]:
    deleted = await queue_service.delete_queue_item(db, item_id)
    if not deleted:
        raise HTTPException(404, "队列条目不存在")
    return {"status": "deleted"}


@router.patch("/queue/{item_id}", response_model=QueueItemResponse)
async def update_queue_item(
    item_id: int, data: QueueItemPriorityUpdate, db: AsyncSession = DBDep
) -> QueueItemResponse:
    item = await queue_service.update_priority(db, item_id, data.priority)
    if not item:
        raise HTTPException(404, "队列条目不存在")
    return QueueItemResponse.model_validate(item)


@router.post("/queue/pop", response_model=QueueItemResponse | None)
async def pop_queue_item(
    platform: str = "telegram", db: AsyncSession = DBDep
) -> QueueItemResponse | None:
    """Bot 调用：取出下一条 pending 条目并标记为 processing。"""
    item = await queue_service.pop_next_item(db, platform)
    if not item:
        return None
    return QueueItemResponse.model_validate(item)


@router.post("/queue/{item_id}/done", response_model=dict[str, str])
async def mark_queue_done(item_id: int, db: AsyncSession = DBDep) -> dict[str, str]:
    await queue_service.mark_done(db, item_id)
    return {"status": "done"}


@router.post("/queue/{item_id}/failed", response_model=dict[str, str])
async def mark_queue_failed(
    item_id: int, error: str = "", db: AsyncSession = DBDep
) -> dict[str, str]:
    await queue_service.mark_failed(db, item_id, error)
    return {"status": "failed"}


@router.get("/queue/next-times", response_model=NextTimesResponse)
async def get_next_post_times(
    count: int = 5,
    platform: str = "telegram",
    db: AsyncSession = DBDep,
) -> NextTimesResponse:
    """预测接下来 N 次队列发布的时间点。"""
    settings = await bot_service.get_all_settings(db)
    interval_minutes = int(settings.get("queue_interval_minutes", "120"))

    # 取最近一次发布时间
    logs, _ = await bot_service.get_post_logs(db, page=1, page_size=1)
    if logs:
        last_post = logs[0].posted_at
        if last_post.tzinfo is None:
            last_post = last_post.replace(tzinfo=UTC)
    else:
        last_post = datetime.now(UTC)

    _, pending_count = await queue_service.list_queue(db, status="pending", platform=platform)

    times: list[datetime] = []
    next_time = last_post + timedelta(minutes=interval_minutes)
    now = datetime.now(UTC)
    if next_time < now:
        next_time = now + timedelta(minutes=1)

    for i in range(min(count, pending_count)):
        times.append(next_time + timedelta(minutes=interval_minutes * i))

    return NextTimesResponse(
        times=times,
        interval_minutes=interval_minutes,
        pending_count=pending_count,
    )


@router.get("/post-logs/today-count")
async def get_today_post_count(
    platform: str = "telegram", db: AsyncSession = DBDep
) -> dict[str, int]:
    count = await queue_service.get_today_post_count(db, platform)
    return {"count": count}


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
