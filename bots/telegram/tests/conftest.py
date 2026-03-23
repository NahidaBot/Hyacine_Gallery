"""Shared fixtures for bot tests."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# Bot 代码使用本地导入，需将 bot 根目录加入 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def mock_client():
    """Mock GalleryClient with all methods as AsyncMock."""
    from client import GalleryClient

    client = MagicMock(spec=GalleryClient)
    # Make all async methods AsyncMock
    client.get_artwork = AsyncMock(return_value=None)
    client.get_random = AsyncMock(return_value=None)
    client.create_artwork = AsyncMock()
    client.search_artworks = AsyncMock(return_value=([], 0))
    client.semantic_search = AsyncMock(return_value=[])
    client.search_by_image = AsyncMock(return_value=[])
    client.reverse_search_image = AsyncMock(return_value=[])
    client.import_artwork = AsyncMock()
    client.resolve_channel = AsyncMock(return_value=None)
    client.create_post_log = AsyncMock()
    client.pop_queue_item = AsyncMock(return_value=None)
    client.mark_queue_done = AsyncMock()
    client.mark_queue_failed = AsyncMock()
    client.get_today_post_count = AsyncMock(return_value=0)
    client.check_admin = AsyncMock(return_value=True)
    client.get_bot_settings = AsyncMock(return_value={})
    # minimal JPEG-like bytes
    client.download_image = AsyncMock(return_value=b"\xff\xd8\xff" + b"\x00" * 100)
    client.close = AsyncMock()
    return client


@pytest.fixture
def mock_context(mock_client):
    """Mock ContextTypes.DEFAULT_TYPE context."""
    context = MagicMock()
    context.bot_data = {
        "gallery_client": mock_client,
        "bot_settings": {},
        "last_post_time": 0.0,
        "last_queue_post_time": 0.0,
        "channel_posts": {},
    }
    context.args = []
    context.bot = AsyncMock()
    # Make bot.send_photo return a message with message_id
    mock_msg = MagicMock()
    mock_msg.message_id = 42
    context.bot.send_photo = AsyncMock(return_value=mock_msg)
    context.bot.send_media_group = AsyncMock(return_value=[mock_msg])
    context.bot.get_file = AsyncMock()
    return context


@pytest.fixture
def mock_update():
    """Mock Update with effective_message and effective_user."""
    update = MagicMock()
    update.effective_user = MagicMock()
    update.effective_user.id = 12345
    update.effective_user.username = "testuser"
    update.effective_message = AsyncMock()
    update.effective_message.reply_text = AsyncMock()
    update.effective_message.reply_photo = AsyncMock()
    update.effective_message.reply_media_group = AsyncMock()
    update.effective_message.reply_document = AsyncMock()
    update.effective_message.photo = [MagicMock(file_id="photo_123")]
    update.effective_message.caption = ""
    update.effective_message.text = ""
    update.effective_message.forward_origin = None
    update.message = update.effective_message
    update.callback_query = None
    return update


def _make_artwork_data(**kwargs):
    """Helper to create ArtworkData instances for tests."""
    from client import ArtworkData, ImageData, TagData

    defaults = {
        "id": 1,
        "platform": "pixiv",
        "pid": "12345",
        "title": "Test Art",
        "title_zh": "",
        "author": "Artist",
        "source_url": "https://pixiv.net/artworks/12345",
        "is_nsfw": False,
        "is_ai": False,
        "images": [
            ImageData(
                id=1,
                page_index=0,
                url_original="https://example.com/img.jpg",
                url_thumb="https://example.com/thumb.jpg",
            )
        ],
        "tags": [TagData(id=1, name="landscape", type="general")],
    }
    defaults.update(kwargs)
    return ArtworkData(**defaults)
