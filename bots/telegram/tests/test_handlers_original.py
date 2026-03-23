"""Tests for the original image reply handler (评论群原图自动回复)."""

from unittest.mock import AsyncMock, MagicMock

from telegram import MessageOriginChannel

from handlers.original import _ext_from_url, channel_post_handler
from tests.conftest import _make_artwork_data

# ── _ext_from_url ───────────────────────────────────────────────────


def test_ext_from_url():
    assert _ext_from_url("https://example.com/img.webp") == ".webp"
    assert _ext_from_url("https://example.com/path/photo.png") == ".png"
    assert _ext_from_url("https://example.com/img") == ""
    assert _ext_from_url("https://example.com/img.jpg?token=abc") == ".jpg"


# ── channel_post_handler: 缓存命中 ─────────────────────────────────


async def test_channel_post_with_cache(mock_update, mock_context, mock_client):
    """forward_origin 是 MessageOriginChannel 且缓存中有对应作品，应发送文档。"""
    artwork = _make_artwork_data()
    mock_context.bot_data["channel_posts"] = {42: artwork}

    # 构造 MessageOriginChannel forward_origin
    forward_origin = MagicMock(spec=MessageOriginChannel)
    forward_origin.message_id = 42
    mock_update.effective_message.forward_origin = forward_origin

    mock_client.download_image = AsyncMock(return_value=b"\xff\xd8\xff" + b"\x00" * 50)

    await channel_post_handler(mock_update, mock_context)

    # 单张图应调用 reply_document
    mock_update.effective_message.reply_document.assert_awaited_once()
    # 缓存中应被弹出
    assert 42 not in mock_context.bot_data["channel_posts"]


# ── channel_post_handler: 缓存未命中 ───────────────────────────────


async def test_channel_post_no_cache(mock_update, mock_context, mock_client):
    """缓存中没有对应作品，不应发送任何东西。"""
    mock_context.bot_data["channel_posts"] = {}

    forward_origin = MagicMock(spec=MessageOriginChannel)
    forward_origin.message_id = 999
    mock_update.effective_message.forward_origin = forward_origin

    await channel_post_handler(mock_update, mock_context)

    mock_update.effective_message.reply_document.assert_not_awaited()
    mock_update.effective_message.reply_media_group.assert_not_awaited()


# ── channel_post_handler: 非 MessageOriginChannel ──────────────────


async def test_channel_post_not_channel_origin(mock_update, mock_context, mock_client):
    """forward_origin 不是 MessageOriginChannel（如用户转发），不应处理。"""
    mock_update.effective_message.forward_origin = MagicMock()  # 非 MessageOriginChannel spec

    await channel_post_handler(mock_update, mock_context)

    mock_update.effective_message.reply_document.assert_not_awaited()
    mock_client.download_image.assert_not_awaited()
