"""bot_service 单元测试。"""

import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.artwork import ArtworkCreate
from app.schemas.bot import BotChannelCreate, BotChannelUpdate, BotPostLogCreate
from app.services.artwork_service import create_artwork
from app.services.bot_service import (
    create_channel,
    create_post_log,
    delete_channel,
    get_all_settings,
    get_channel_by_id,
    get_channels,
    get_post_logs,
    get_setting,
    get_settings_list,
    resolve_channel,
    set_settings,
    update_channel,
)

# ── 发布日志 ──────────────────────────────────────────────────────


async def test_create_post_log(db: AsyncSession, sample_artwork):
    log = await create_post_log(
        db,
        BotPostLogCreate(
            artwork_id=sample_artwork.id,
            channel_id="-100999",
            message_id="42",
            posted_by="admin",
        ),
    )
    assert log.id is not None
    assert log.artwork_id == sample_artwork.id
    assert log.channel_id == "-100999"
    assert log.bot_platform == "telegram"


async def test_get_post_logs(db: AsyncSession, sample_artwork):
    await create_post_log(
        db,
        BotPostLogCreate(artwork_id=sample_artwork.id, channel_id="-100a", message_id="1"),
    )
    await create_post_log(
        db,
        BotPostLogCreate(artwork_id=sample_artwork.id, channel_id="-100b", message_id="2"),
    )

    logs, total = await get_post_logs(db)
    assert total == 2
    assert len(logs) == 2


async def test_get_post_logs_filter_artwork_id(db: AsyncSession, sample_artwork):
    other = await create_artwork(
        db, ArtworkCreate(platform="pixiv", pid="other_log", title="Other")
    )
    await create_post_log(
        db,
        BotPostLogCreate(artwork_id=sample_artwork.id, channel_id="-100a"),
    )
    await create_post_log(
        db,
        BotPostLogCreate(artwork_id=other.id, channel_id="-100a"),
    )

    logs, total = await get_post_logs(db, artwork_id=sample_artwork.id)
    assert total == 1
    assert logs[0].artwork_id == sample_artwork.id


async def test_get_post_logs_filter_channel_id(db: AsyncSession, sample_artwork):
    await create_post_log(
        db,
        BotPostLogCreate(artwork_id=sample_artwork.id, channel_id="-100a"),
    )
    await create_post_log(
        db,
        BotPostLogCreate(artwork_id=sample_artwork.id, channel_id="-100b"),
    )

    logs, total = await get_post_logs(db, channel_id="-100a")
    assert total == 1
    assert logs[0].channel_id == "-100a"


# ── 频道 CRUD ─────────────────────────────────────────────────────


async def test_get_channels(db: AsyncSession, sample_channel):
    channels = await get_channels(db, platform="telegram")
    assert len(channels) >= 1
    assert any(c.id == sample_channel.id for c in channels)


async def test_get_channel_by_id(db: AsyncSession, sample_channel):
    found = await get_channel_by_id(db, sample_channel.id)
    assert found is not None
    assert found.channel_id == sample_channel.channel_id


async def test_get_channel_by_id_not_found(db: AsyncSession):
    assert await get_channel_by_id(db, 999999) is None


async def test_create_channel(db: AsyncSession):
    ch = await create_channel(
        db,
        BotChannelCreate(
            channel_id="-100new",
            name="New Channel",
            is_default=False,
            priority=5,
            conditions={"is_nsfw": True},
            enabled=True,
        ),
    )
    assert ch.id is not None
    assert ch.channel_id == "-100new"
    assert ch.name == "New Channel"
    assert json.loads(ch.conditions) == {"is_nsfw": True}


async def test_update_channel(db: AsyncSession, sample_channel):
    updated = await update_channel(
        db, sample_channel.id, BotChannelUpdate(name="Updated Name", priority=99)
    )
    assert updated is not None
    assert updated.name == "Updated Name"
    assert updated.priority == 99


async def test_update_channel_not_found(db: AsyncSession):
    result = await update_channel(db, 999999, BotChannelUpdate(name="X"))
    assert result is None


async def test_delete_channel(db: AsyncSession, sample_channel):
    assert await delete_channel(db, sample_channel.id) is True
    assert await get_channel_by_id(db, sample_channel.id) is None


async def test_delete_channel_not_found(db: AsyncSession):
    assert await delete_channel(db, 999999) is False


# ── resolve_channel ───────────────────────────────────────────────


async def test_resolve_channel_default(db: AsyncSession, sample_artwork, sample_channel):
    """空 conditions 的默认频道应匹配任意作品。"""
    result = await resolve_channel(db, sample_artwork)
    assert result is not None
    assert result.id == sample_channel.id


async def test_resolve_channel_conditions_is_nsfw(db: AsyncSession):
    nsfw_ch = await create_channel(
        db,
        BotChannelCreate(
            channel_id="-100nsfw",
            name="NSFW",
            conditions={"is_nsfw": True},
            priority=0,
        ),
    )
    artwork = await create_artwork(
        db,
        ArtworkCreate(platform="pixiv", pid="nsfw_1", is_nsfw=True),
    )
    result = await resolve_channel(db, artwork)
    assert result is not None
    assert result.id == nsfw_ch.id


async def test_resolve_channel_conditions_is_ai(db: AsyncSession):
    ai_ch = await create_channel(
        db,
        BotChannelCreate(
            channel_id="-100ai",
            name="AI",
            conditions={"is_ai": True},
            priority=0,
        ),
    )
    artwork = await create_artwork(
        db,
        ArtworkCreate(platform="pixiv", pid="ai_1", is_ai=True),
    )
    result = await resolve_channel(db, artwork)
    assert result is not None
    assert result.id == ai_ch.id


async def test_resolve_channel_conditions_tags_any(db: AsyncSession):
    ch = await create_channel(
        db,
        BotChannelCreate(
            channel_id="-100tags_any",
            name="Tags Any",
            conditions={"tags_any": ["landscape"]},
            priority=0,
        ),
    )
    artwork = await create_artwork(
        db,
        ArtworkCreate(platform="pixiv", pid="ta_1", tags=["landscape", "sky"]),
    )
    result = await resolve_channel(db, artwork)
    assert result is not None
    assert result.id == ch.id


async def test_resolve_channel_conditions_tags_all(db: AsyncSession):
    ch = await create_channel(
        db,
        BotChannelCreate(
            channel_id="-100tags_all",
            name="Tags All",
            conditions={"tags_all": ["landscape", "sky"]},
            priority=0,
        ),
    )
    artwork = await create_artwork(
        db,
        ArtworkCreate(platform="pixiv", pid="tall_1", tags=["landscape", "sky", "cloud"]),
    )
    result = await resolve_channel(db, artwork)
    assert result is not None
    assert result.id == ch.id


async def test_resolve_channel_conditions_platform(db: AsyncSession):
    ch = await create_channel(
        db,
        BotChannelCreate(
            channel_id="-100plat",
            name="Pixiv Only",
            conditions={"platform": "pixiv"},
            priority=0,
        ),
    )
    artwork = await create_artwork(
        db,
        ArtworkCreate(platform="pixiv", pid="plat_1"),
    )
    result = await resolve_channel(db, artwork)
    assert result is not None
    assert result.id == ch.id


async def test_resolve_channel_conditions_combined(db: AsyncSession):
    ch = await create_channel(
        db,
        BotChannelCreate(
            channel_id="-100combo",
            name="Combined",
            conditions={"is_nsfw": True, "platform": "pixiv"},
            priority=0,
        ),
    )
    artwork = await create_artwork(
        db,
        ArtworkCreate(platform="pixiv", pid="combo_1", is_nsfw=True),
    )
    result = await resolve_channel(db, artwork)
    assert result is not None
    assert result.id == ch.id


async def test_resolve_channel_no_match(db: AsyncSession, sample_channel):
    """条件不匹配时回退到默认频道。"""
    # 添加一个有条件的频道（不匹配 sample_artwork）
    await create_channel(
        db,
        BotChannelCreate(
            channel_id="-100strict",
            name="Strict",
            conditions={"is_nsfw": True},
            priority=0,
        ),
    )
    artwork = await create_artwork(
        db,
        ArtworkCreate(platform="pixiv", pid="nomatch_1", is_nsfw=False),
    )
    result = await resolve_channel(db, artwork)
    # 应该回退到 sample_channel（默认频道）
    assert result is not None
    assert result.id == sample_channel.id


async def test_resolve_channel_disabled_skipped(db: AsyncSession, sample_channel):
    """禁用的频道即使条件匹配也应被跳过。"""
    disabled = await create_channel(
        db,
        BotChannelCreate(
            channel_id="-100disabled",
            name="Disabled",
            conditions={"is_nsfw": True},
            priority=0,
            enabled=False,
        ),
    )
    artwork = await create_artwork(
        db,
        ArtworkCreate(platform="pixiv", pid="dis_1", is_nsfw=True),
    )
    result = await resolve_channel(db, artwork)
    # 跳过禁用频道，回退到默认
    assert result is not None
    assert result.id != disabled.id
    assert result.id == sample_channel.id


async def test_resolve_channel_none(db: AsyncSession):
    """没有任何频道时返回 None。"""
    artwork = await create_artwork(
        db,
        ArtworkCreate(platform="pixiv", pid="none_1"),
    )
    result = await resolve_channel(db, artwork)
    assert result is None


# ── 设置 ──────────────────────────────────────────────────────────


async def test_settings_crud(db: AsyncSession):
    await set_settings(db, {"interval": "30", "max_daily": "10"})

    val = await get_setting(db, "interval")
    assert val == "30"

    all_s = await get_all_settings(db)
    assert all_s["interval"] == "30"
    assert all_s["max_daily"] == "10"

    s_list = await get_settings_list(db)
    keys = {s.key for s in s_list}
    assert "interval" in keys
    assert "max_daily" in keys

    # 更新已有 key
    await set_settings(db, {"interval": "60"})
    assert await get_setting(db, "interval") == "60"


async def test_get_setting_default(db: AsyncSession):
    val = await get_setting(db, "nonexistent_key", default="fallback")
    assert val == "fallback"
