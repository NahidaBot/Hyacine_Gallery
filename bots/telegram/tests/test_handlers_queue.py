"""Tests for the post queue processor job."""

import time
from unittest.mock import AsyncMock, patch

from client import QueueItem
from handlers.queue import process_post_queue
from tests.conftest import _make_artwork_data


def _make_queue_item(**kwargs):
    defaults = {
        "id": 10,
        "artwork_id": 1,
        "platform": "telegram",
        "channel_id": "@testchan",
        "priority": 0,
        "status": "processing",
        "added_by": "admin",
    }
    defaults.update(kwargs)
    return QueueItem(**defaults)


# ── 队列禁用 ────────────────────────────────────────────────────────


async def test_queue_disabled(mock_context, mock_client):
    mock_context.bot_data["bot_settings"] = {"queue_enabled": "false"}
    await process_post_queue(mock_context)
    mock_client.pop_queue_item.assert_not_awaited()


# ── 发布间隔不足 ────────────────────────────────────────────────────


async def test_queue_interval_not_met(mock_context, mock_client):
    mock_context.bot_data["bot_settings"] = {
        "queue_enabled": "true",
        "queue_interval_minutes": "60",
    }
    mock_context.bot_data["last_queue_post_time"] = time.time()  # 刚发布过
    await process_post_queue(mock_context)
    mock_client.pop_queue_item.assert_not_awaited()


# ── 每日上限已达 ────────────────────────────────────────────────────


async def test_queue_daily_limit(mock_context, mock_client):
    mock_context.bot_data["bot_settings"] = {
        "queue_enabled": "true",
        "queue_interval_minutes": "0",
        "queue_daily_limit": "5",
    }
    mock_context.bot_data["last_queue_post_time"] = 0.0
    mock_client.get_today_post_count = AsyncMock(return_value=5)
    await process_post_queue(mock_context)
    mock_client.pop_queue_item.assert_not_awaited()


# ── 队列为空 ────────────────────────────────────────────────────────


async def test_queue_empty(mock_context, mock_client):
    mock_context.bot_data["bot_settings"] = {"queue_enabled": "true", "queue_interval_minutes": "0"}
    mock_context.bot_data["last_queue_post_time"] = 0.0
    mock_client.pop_queue_item = AsyncMock(return_value=None)
    await process_post_queue(mock_context)
    mock_client.pop_queue_item.assert_awaited_once()
    mock_client.mark_queue_done.assert_not_awaited()


# ── 成功发布 ────────────────────────────────────────────────────────


async def test_queue_success(mock_context, mock_client):
    """取出队列条目 -> 获取作品 -> 发布到频道 -> 标记完成。"""
    import io

    from PIL import Image

    # 生成有效 JPEG 字节
    img = Image.new("RGB", (10, 10), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    jpeg_bytes = buf.getvalue()

    mock_context.bot_data["bot_settings"] = {"queue_enabled": "true", "queue_interval_minutes": "0"}
    mock_context.bot_data["last_queue_post_time"] = 0.0

    item = _make_queue_item()
    artwork = _make_artwork_data()

    mock_client.pop_queue_item = AsyncMock(return_value=item)
    mock_client.get_artwork = AsyncMock(return_value=artwork)
    mock_client.download_image = AsyncMock(return_value=jpeg_bytes)
    mock_client.resolve_channel = AsyncMock(return_value=None)

    await process_post_queue(mock_context)

    mock_client.mark_queue_done.assert_awaited_once_with(item.id)
    mock_client.create_post_log.assert_awaited_once()


# ── 作品不存在 ──────────────────────────────────────────────────────


async def test_queue_artwork_not_found(mock_context, mock_client):
    mock_context.bot_data["bot_settings"] = {"queue_enabled": "true", "queue_interval_minutes": "0"}
    mock_context.bot_data["last_queue_post_time"] = 0.0

    item = _make_queue_item()
    mock_client.pop_queue_item = AsyncMock(return_value=item)
    mock_client.get_artwork = AsyncMock(return_value=None)

    await process_post_queue(mock_context)

    mock_client.mark_queue_failed.assert_awaited_once()
    args = mock_client.mark_queue_failed.call_args
    assert args[0][0] == item.id


# ── 无可用频道 ──────────────────────────────────────────────────────


async def test_queue_no_channel(mock_context, mock_client):
    mock_context.bot_data["bot_settings"] = {"queue_enabled": "true", "queue_interval_minutes": "0"}
    mock_context.bot_data["last_queue_post_time"] = 0.0

    item = _make_queue_item(channel_id="")
    artwork = _make_artwork_data()

    mock_client.pop_queue_item = AsyncMock(return_value=item)
    mock_client.get_artwork = AsyncMock(return_value=artwork)
    mock_client.resolve_channel = AsyncMock(return_value=None)

    # 回退频道也设为空
    with patch("handlers.artwork.bot_settings") as mock_settings:
        mock_settings.telegram_channel = ""
        await process_post_queue(mock_context)

    mock_client.mark_queue_failed.assert_awaited_once()


# ── 发布异常 ────────────────────────────────────────────────────────


async def test_queue_post_exception(mock_context, mock_client):
    import io

    from PIL import Image

    img = Image.new("RGB", (10, 10), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    jpeg_bytes = buf.getvalue()

    mock_context.bot_data["bot_settings"] = {"queue_enabled": "true", "queue_interval_minutes": "0"}
    mock_context.bot_data["last_queue_post_time"] = 0.0

    item = _make_queue_item()
    artwork = _make_artwork_data()

    mock_client.pop_queue_item = AsyncMock(return_value=item)
    mock_client.get_artwork = AsyncMock(return_value=artwork)
    mock_client.download_image = AsyncMock(return_value=jpeg_bytes)
    mock_client.resolve_channel = AsyncMock(return_value=None)

    # 让 send_photo 抛出异常
    mock_context.bot.send_photo = AsyncMock(side_effect=Exception("Telegram API error"))

    await process_post_queue(mock_context)

    mock_client.mark_queue_failed.assert_awaited_once()
