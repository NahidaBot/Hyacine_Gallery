import json

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.artwork import Artwork, BotPostLog
from app.models.bot import BotChannel, BotSetting
from app.schemas.bot import BotChannelCreate, BotChannelUpdate, BotPostLogCreate


# --- 发布日志 ---


async def create_post_log(db: AsyncSession, data: BotPostLogCreate) -> BotPostLog:
    log = BotPostLog(
        artwork_id=data.artwork_id,
        bot_platform=data.bot_platform,
        channel_id=data.channel_id,
        message_id=data.message_id,
        message_link=data.message_link,
        posted_by=data.posted_by,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


async def get_post_logs(
    db: AsyncSession,
    *,
    artwork_id: int | None = None,
    channel_id: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[BotPostLog], int]:
    query = select(BotPostLog)
    if artwork_id:
        query = query.where(BotPostLog.artwork_id == artwork_id)
    if channel_id:
        query = query.where(BotPostLog.channel_id == channel_id)

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    query = query.order_by(BotPostLog.posted_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    return list(result.scalars().all()), total


# --- 机器人频道 ---


async def get_channels(
    db: AsyncSession, platform: str = "telegram"
) -> list[BotChannel]:
    query = (
        select(BotChannel)
        .where(BotChannel.platform == platform)
        .order_by(BotChannel.priority.asc())
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_channel_by_id(db: AsyncSession, channel_id: int) -> BotChannel | None:
    result = await db.execute(select(BotChannel).where(BotChannel.id == channel_id))
    return result.scalar_one_or_none()


async def create_channel(db: AsyncSession, data: BotChannelCreate) -> BotChannel:
    channel = BotChannel(
        platform=data.platform,
        channel_id=data.channel_id,
        name=data.name,
        is_default=data.is_default,
        priority=data.priority,
        conditions=json.dumps(data.conditions, ensure_ascii=False),
        enabled=data.enabled,
    )
    db.add(channel)
    await db.commit()
    await db.refresh(channel)
    return channel


async def update_channel(
    db: AsyncSession, channel_id: int, data: BotChannelUpdate
) -> BotChannel | None:
    channel = await get_channel_by_id(db, channel_id)
    if not channel:
        return None

    for field in ("channel_id", "name", "is_default", "priority", "enabled"):
        value = getattr(data, field)
        if value is not None:
            setattr(channel, field, value)

    if data.conditions is not None:
        channel.conditions = json.dumps(data.conditions, ensure_ascii=False)

    await db.commit()
    await db.refresh(channel)
    return channel


async def delete_channel(db: AsyncSession, channel_id: int) -> bool:
    channel = await get_channel_by_id(db, channel_id)
    if not channel:
        return False
    await db.delete(channel)
    await db.commit()
    return True


def _match_conditions(conditions: dict, artwork: Artwork) -> bool:
    """判断作品是否匹配频道的路由条件。"""
    if not conditions:
        return True

    if "is_ai" in conditions and artwork.is_ai != conditions["is_ai"]:
        return False
    if "is_nsfw" in conditions and artwork.is_nsfw != conditions["is_nsfw"]:
        return False

    if "tags_any" in conditions:
        artwork_tag_names = {t.name for t in artwork.tags}
        if not artwork_tag_names.intersection(conditions["tags_any"]):
            return False

    if "tags_all" in conditions:
        artwork_tag_names = {t.name for t in artwork.tags}
        if not set(conditions["tags_all"]).issubset(artwork_tag_names):
            return False

    if "platform" in conditions and artwork.platform != conditions["platform"]:
        return False

    return True


async def resolve_channel(
    db: AsyncSession, artwork: Artwork, platform: str = "telegram"
) -> BotChannel | None:
    """根据路由规则查找作品匹配的第一个频道。"""
    channels = await get_channels(db, platform)

    default_channel: BotChannel | None = None
    for channel in channels:
        if not channel.enabled:
            continue

        conditions = json.loads(channel.conditions) if channel.conditions else {}

        if channel.is_default and not default_channel:
            default_channel = channel

        if conditions and _match_conditions(conditions, artwork):
            return channel

    return default_channel


# --- 机器人设置 ---


async def get_all_settings(db: AsyncSession) -> dict[str, str]:
    result = await db.execute(select(BotSetting))
    return {s.key: s.value for s in result.scalars().all()}


async def get_setting(db: AsyncSession, key: str, default: str = "") -> str:
    result = await db.execute(select(BotSetting).where(BotSetting.key == key))
    setting = result.scalar_one_or_none()
    return setting.value if setting else default


async def set_settings(db: AsyncSession, data: dict[str, str]) -> None:
    for key, value in data.items():
        result = await db.execute(select(BotSetting).where(BotSetting.key == key))
        setting = result.scalar_one_or_none()
        if setting:
            setting.value = value
        else:
            db.add(BotSetting(key=key, value=value))
    await db.commit()


async def get_settings_list(db: AsyncSession) -> list[BotSetting]:
    result = await db.execute(select(BotSetting).order_by(BotSetting.key))
    return list(result.scalars().all())
