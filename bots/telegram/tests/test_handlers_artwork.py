"""Tests for artwork command handlers (/random, /post, /import)."""

import io
from unittest.mock import AsyncMock, patch

from PIL import Image

from handlers.artwork import (
    _get_setting,
    _is_admin,
    _message_link,
    _to_hashtag,
    format_caption,
    import_command,
    post_command,
    random_command,
)
from tests.conftest import _make_artwork_data


def _make_jpeg_bytes():
    """生成一个最小的有效 JPEG 字节流。"""
    img = Image.new("RGB", (10, 10), color="red")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


# ── _to_hashtag ─────────────────────────────────────────────────────


def test_to_hashtag_basic():
    assert _to_hashtag("tag name") == "#tag_name"
    assert _to_hashtag("tag-with-dash") == "#tag_with_dash"
    assert _to_hashtag("中文标签") == "#中文标签"
    assert _to_hashtag("") == ""


def test_to_hashtag_special_chars():
    # 斜杠等非 \w 字符应被移除
    assert _to_hashtag("a/b") == "#ab"
    assert _to_hashtag("hello.world") == "#helloworld"
    assert _to_hashtag("a&b!c") == "#abc"


# ── format_caption ──────────────────────────────────────────────────


def test_format_caption():
    artwork = _make_artwork_data()
    caption = format_caption(artwork)
    assert "Test Art" in caption
    assert "Artist" in caption
    assert "#landscape" in caption
    assert "source" in caption
    assert "pixiv.net" in caption


def test_format_caption_no_author():
    artwork = _make_artwork_data(author="")
    caption = format_caption(artwork)
    assert "Test Art" in caption
    assert " by " not in caption


def test_format_caption_nsfw_ai():
    artwork = _make_artwork_data(is_nsfw=True, is_ai=True)
    caption = format_caption(artwork)
    assert "NSFW" in caption
    assert "AI" in caption


def test_format_caption_with_tail():
    artwork = _make_artwork_data()
    caption = format_caption(artwork, tail_text="@mychannel")
    assert "@mychannel" in caption


# ── _message_link ───────────────────────────────────────────────────


def test_message_link_public():
    link = _message_link("@channel", 42)
    assert link == "https://t.me/channel/42"


def test_message_link_private():
    link = _message_link("-1001234567890", 42)
    assert link == "https://t.me/c/1234567890/42"


# ── random_command ──────────────────────────────────────────────────


async def test_random_command(mock_update, mock_context, mock_client):
    artwork = _make_artwork_data()
    mock_client.get_random = AsyncMock(return_value=artwork)
    mock_client.download_image = AsyncMock(return_value=_make_jpeg_bytes())
    await random_command(mock_update, mock_context)
    # send_artwork 应调用 reply_photo（单图）
    mock_update.effective_message.reply_photo.assert_awaited_once()


async def test_random_command_empty(mock_update, mock_context, mock_client):
    mock_client.get_random = AsyncMock(return_value=None)
    await random_command(mock_update, mock_context)
    mock_update.message.reply_text.assert_awaited_once()
    text = mock_update.message.reply_text.call_args[0][0]
    assert "暂无" in text


# ── _is_admin ───────────────────────────────────────────────────────


async def test_is_admin_backend(mock_context, mock_client):
    mock_client.check_admin = AsyncMock(return_value=True)
    assert await _is_admin(12345, mock_context) is True
    mock_client.check_admin.assert_awaited_once_with(12345)


async def test_is_admin_fallback(mock_context, mock_client):
    mock_client.check_admin = AsyncMock(side_effect=Exception("connection error"))
    with patch("handlers.artwork.bot_settings") as mock_settings:
        mock_settings.telegram_admin_chats = [12345]
        assert await _is_admin(12345, mock_context) is True

    # 不在列表中的用户
    mock_client.check_admin = AsyncMock(side_effect=Exception("connection error"))
    with patch("handlers.artwork.bot_settings") as mock_settings:
        mock_settings.telegram_admin_chats = [99999]
        assert await _is_admin(12345, mock_context) is False


# ── post_command ────────────────────────────────────────────────────


async def test_post_command_no_admin(mock_update, mock_context, mock_client):
    mock_client.check_admin = AsyncMock(return_value=False)
    with patch("handlers.artwork.bot_settings") as mock_settings:
        mock_settings.telegram_admin_chats = []
        await post_command(mock_update, mock_context)
    mock_update.message.reply_text.assert_awaited()
    text = mock_update.message.reply_text.call_args[0][0]
    assert "权限不足" in text


# ── import_command ──────────────────────────────────────────────────


async def test_import_command_no_url(mock_update, mock_context, mock_client):
    mock_update.message.text = "/import"
    mock_client.check_admin = AsyncMock(return_value=True)
    await import_command(mock_update, mock_context)
    mock_update.message.reply_text.assert_awaited()
    text = mock_update.message.reply_text.call_args[0][0]
    assert "用法" in text


# ── _get_setting ────────────────────────────────────────────────────


def test_get_setting(mock_context):
    mock_context.bot_data["bot_settings"] = {"queue_enabled": "true"}
    assert _get_setting(mock_context, "queue_enabled") == "true"


def test_get_setting_default(mock_context):
    mock_context.bot_data["bot_settings"] = {}
    assert _get_setting(mock_context, "nonexistent", "fallback") == "fallback"
