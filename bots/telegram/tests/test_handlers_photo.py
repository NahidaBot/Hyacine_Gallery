"""Tests for photo message handlers (以图搜图, 转发导入, 回调按钮)."""

import io
from unittest.mock import AsyncMock, MagicMock

from client import SimilarArtwork
from handlers.photo import callback_handler, photo_handler
from tests.conftest import _make_artwork_data


def _make_file_mock(image_bytes: bytes):
    """创建模拟的 Telegram File 对象，download_to_memory 写入字节。"""
    file_mock = MagicMock()

    async def _download_to_memory(buf: io.BytesIO):
        buf.write(image_bytes)

    file_mock.download_to_memory = AsyncMock(side_effect=_download_to_memory)
    return file_mock


def _similar_artwork(**kwargs):
    defaults = {
        "artwork_id": 1,
        "distance": 3,
        "platform": "pixiv",
        "pid": "99999",
        "title": "Found Art",
        "thumb_url": "https://img.example/thumb.jpg",
    }
    defaults.update(kwargs)
    return SimilarArtwork(**defaults)


# ── photo_handler: pHash 搜索有结果 ────────────────────────────────


async def test_photo_handler_phash_results(mock_update, mock_context, mock_client):
    """非转发图片，pHash 搜索返回结果，应展示按钮列表。"""
    mock_update.effective_message.forward_origin = None
    mock_client.check_admin = AsyncMock(return_value=False)
    mock_client.search_by_image = AsyncMock(return_value=[_similar_artwork()])

    # 设置 get_file 和 download_to_memory
    file_mock = _make_file_mock(b"\xff\xd8\xff" + b"\x00" * 50)
    mock_context.bot.get_file = AsyncMock(return_value=file_mock)

    # reply_text 返回可 edit 的状态消息
    status_msg = AsyncMock()
    mock_update.effective_message.reply_text = AsyncMock(return_value=status_msg)

    await photo_handler(mock_update, mock_context)

    # 状态消息应被 edit 为搜索结果
    status_msg.edit_text.assert_awaited()
    call_kwargs = status_msg.edit_text.call_args
    assert "相似作品" in call_kwargs[0][0]
    assert call_kwargs.kwargs.get("reply_markup") is not None


# ── photo_handler: pHash 无结果，非管理员 ────────────────────────────


async def test_photo_handler_phash_no_results_non_admin(mock_update, mock_context, mock_client):
    """非管理员发送图片，pHash 无结果，应回复"未找到"。"""
    mock_update.effective_message.forward_origin = None
    mock_client.check_admin = AsyncMock(return_value=False)
    mock_client.search_by_image = AsyncMock(return_value=[])

    file_mock = _make_file_mock(b"\xff\xd8\xff" + b"\x00" * 50)
    mock_context.bot.get_file = AsyncMock(return_value=file_mock)

    status_msg = AsyncMock()
    mock_update.effective_message.reply_text = AsyncMock(return_value=status_msg)

    await photo_handler(mock_update, mock_context)

    status_msg.edit_text.assert_awaited()
    text = status_msg.edit_text.call_args[0][0]
    assert "未找到" in text


# ── photo_handler: 管理员转发带 URL ─────────────────────────────────


async def test_photo_handler_forwarded_with_url(mock_update, mock_context, mock_client):
    """管理员转发了带链接的消息，应展示导入按钮。"""
    mock_update.effective_message.forward_origin = MagicMock()  # 非 None 表示转发
    mock_update.effective_message.caption = "https://pixiv.net/artworks/12345"
    mock_client.check_admin = AsyncMock(return_value=True)

    file_mock = _make_file_mock(b"\xff\xd8\xff" + b"\x00" * 50)
    mock_context.bot.get_file = AsyncMock(return_value=file_mock)

    await photo_handler(mock_update, mock_context)

    mock_update.effective_message.reply_text.assert_awaited()
    call_kwargs = mock_update.effective_message.reply_text.call_args
    assert "导入" in call_kwargs[0][0] or call_kwargs.kwargs.get("reply_markup") is not None


# ── callback_handler: dismiss ───────────────────────────────────────


async def test_callback_dismiss(mock_update, mock_context):
    """callback_data="dismiss" 应移除 reply_markup。"""
    query = AsyncMock()
    query.data = "dismiss"
    query.answer = AsyncMock()
    query.edit_message_reply_markup = AsyncMock()
    mock_update.callback_query = query

    await callback_handler(mock_update, mock_context)

    query.answer.assert_awaited_once()
    query.edit_message_reply_markup.assert_awaited_once_with(reply_markup=None)


# ── callback_handler: view ──────────────────────────────────────────


async def test_callback_view(mock_update, mock_context, mock_client):
    """callback_data="view_1" 应获取作品并回复信息。"""
    artwork = _make_artwork_data()
    mock_client.get_artwork = AsyncMock(return_value=artwork)

    query = AsyncMock()
    query.data = "view_1"
    query.answer = AsyncMock()
    query.message = AsyncMock()
    query.message.reply_text = AsyncMock()
    mock_update.callback_query = query

    await callback_handler(mock_update, mock_context)

    query.answer.assert_awaited_once()
    mock_client.get_artwork.assert_awaited_once_with(1)
    query.message.reply_text.assert_awaited_once()
    text = query.message.reply_text.call_args[0][0]
    assert "Test Art" in text


# ── callback_handler: import ────────────────────────────────────────


async def test_callback_import(mock_update, mock_context, mock_client):
    """callback_data="imp:key" 应从 pending_urls 取出 URL 并导入。"""
    mock_context.bot_data["pending_urls"] = {"abc12345": "https://pixiv.net/artworks/99999"}

    artwork = _make_artwork_data()
    mock_client.import_artwork = AsyncMock(return_value=artwork)
    mock_client.check_admin = AsyncMock(return_value=True)

    query = AsyncMock()
    query.data = "imp:abc12345"
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    query.from_user = MagicMock()
    query.from_user.id = 12345
    mock_update.callback_query = query

    await callback_handler(mock_update, mock_context)

    query.answer.assert_awaited_once()
    mock_client.import_artwork.assert_awaited_once_with("https://pixiv.net/artworks/99999")
    query.edit_message_text.assert_awaited()
    text = query.edit_message_text.call_args[0][0]
    assert "已导入" in text


# ── callback_handler: import expired ────────────────────────────────


async def test_callback_import_expired(mock_update, mock_context, mock_client):
    """key 不在 pending_urls 中，应提示"已过期"。"""
    mock_context.bot_data["pending_urls"] = {}

    query = AsyncMock()
    query.data = "imp:nonexistent"
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    mock_update.callback_query = query

    await callback_handler(mock_update, mock_context)

    query.answer.assert_awaited_once()
    query.edit_message_text.assert_awaited()
    text = query.edit_message_text.call_args[0][0]
    assert "已过期" in text
