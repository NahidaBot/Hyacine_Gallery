"""Tests for the GalleryClient HTTP client."""

import httpx
import pytest
import respx

from client import (
    ArtworkData,
    ChannelData,
    GalleryClient,
    QueueItem,
    ReverseSearchResult,
    SimilarArtwork,
)

# ── 固定的测试响应数据 ──────────────────────────────────────────────

_ARTWORK_RESP = {
    "id": 1,
    "platform": "pixiv",
    "pid": "99999",
    "title": "Sunset",
    "title_zh": "夕阳",
    "author": "Alice",
    "source_url": "https://pixiv.net/artworks/99999",
    "is_nsfw": False,
    "is_ai": False,
    "images": [
        {
            "id": 10,
            "page_index": 0,
            "url_original": "https://img.example/original.jpg",
            "url_thumb": "https://img.example/thumb.jpg",
            "url_raw": "https://img.example/raw.png",
            "width": 1920,
            "height": 1080,
        }
    ],
    "tags": [
        {"id": 1, "name": "landscape", "type": "general"},
        {"id": 2, "name": "sunset", "type": "general"},
    ],
}

_CHANNEL_RESP = {
    "id": 1,
    "platform": "telegram",
    "channel_id": "@testchan",
    "name": "Test Channel",
    "is_default": True,
    "priority": 0,
    "conditions": {},
    "enabled": True,
}

_QUEUE_ITEM_RESP = {
    "id": 5,
    "artwork_id": 1,
    "platform": "telegram",
    "channel_id": "@testchan",
    "priority": 0,
    "status": "processing",
    "added_by": "admin",
}


@pytest.fixture
def client():
    return GalleryClient(base_url="http://test", admin_token="tok")


# ── get_artwork ─────────────────────────────────────────────────────


@respx.mock
async def test_get_artwork(client):
    respx.get("http://test/api/artworks/1").mock(
        return_value=httpx.Response(200, json=_ARTWORK_RESP)
    )
    art = await client.get_artwork(1)
    assert art is not None
    assert art.id == 1
    assert art.platform == "pixiv"
    assert art.title == "Sunset"
    assert len(art.images) == 1
    assert len(art.tags) == 2


@respx.mock
async def test_get_artwork_not_found(client):
    respx.get("http://test/api/artworks/999").mock(return_value=httpx.Response(404))
    assert await client.get_artwork(999) is None


# ── get_random ──────────────────────────────────────────────────────


@respx.mock
async def test_get_random(client):
    respx.get("http://test/api/artworks/random").mock(
        return_value=httpx.Response(200, json=_ARTWORK_RESP)
    )
    art = await client.get_random()
    assert art is not None
    assert art.pid == "99999"


@respx.mock
async def test_get_random_not_found(client):
    respx.get("http://test/api/artworks/random").mock(return_value=httpx.Response(404))
    assert await client.get_random() is None


# ── create_artwork ──────────────────────────────────────────────────


@respx.mock
async def test_create_artwork(client):
    route = respx.post("http://test/api/admin/artworks").mock(
        return_value=httpx.Response(200, json=_ARTWORK_RESP)
    )
    art = await client.create_artwork(platform="pixiv", pid="99999", title="Sunset")
    assert art.id == 1
    req_body = route.calls[0].request.content
    assert b"pixiv" in req_body


# ── search_artworks ─────────────────────────────────────────────────


@respx.mock
async def test_search_artworks(client):
    respx.get("http://test/api/artworks").mock(
        return_value=httpx.Response(200, json={"data": [_ARTWORK_RESP], "total": 1})
    )
    artworks, total = await client.search_artworks(q="sunset")
    assert total == 1
    assert len(artworks) == 1
    assert artworks[0].title == "Sunset"


# ── semantic_search ─────────────────────────────────────────────────


@respx.mock
async def test_semantic_search(client):
    respx.get("http://test/api/artworks/search").mock(
        return_value=httpx.Response(
            200,
            json={"results": [{"artwork": _ARTWORK_RESP, "score": 0.95}]},
        )
    )
    results = await client.semantic_search("sunset landscape")
    assert len(results) == 1
    assert results[0][1] == pytest.approx(0.95)


# ── search_by_image ─────────────────────────────────────────────────


@respx.mock
async def test_search_by_image(client):
    respx.post("http://test/api/admin/artworks/search-by-image").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "artwork_id": 1,
                    "distance": 3,
                    "platform": "pixiv",
                    "pid": "99999",
                    "title": "Sunset",
                    "thumb_url": "https://img.example/thumb.jpg",
                }
            ],
        )
    )
    results = await client.search_by_image(b"\xff\xd8fake")
    assert len(results) == 1
    assert isinstance(results[0], SimilarArtwork)
    assert results[0].distance == 3


# ── reverse_search_image ────────────────────────────────────────────


@respx.mock
async def test_reverse_search_image(client):
    respx.post("http://test/api/admin/artworks/reverse-search").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "source_url": "https://pixiv.net/artworks/1",
                    "similarity": 92.5,
                    "platform": "pixiv",
                    "title": "Found",
                    "author": "Bob",
                    "thumb_url": "",
                    "provider": "saucenao",
                }
            ],
        )
    )
    results = await client.reverse_search_image(b"\xff\xd8fake")
    assert len(results) == 1
    assert isinstance(results[0], ReverseSearchResult)
    assert results[0].similarity == pytest.approx(92.5)


# ── import_artwork ──────────────────────────────────────────────────


@respx.mock
async def test_import_artwork(client):
    respx.post("http://test/api/admin/artworks/import").mock(
        return_value=httpx.Response(200, json={"artwork": _ARTWORK_RESP})
    )
    art = await client.import_artwork("https://pixiv.net/artworks/99999", tags=["landscape"])
    assert art.id == 1


# ── resolve_channel ─────────────────────────────────────────────────


@respx.mock
async def test_resolve_channel(client):
    respx.post("http://test/api/admin/bot/channels/resolve").mock(
        return_value=httpx.Response(200, json=_CHANNEL_RESP)
    )
    ch = await client.resolve_channel(1)
    assert ch is not None
    assert isinstance(ch, ChannelData)
    assert ch.channel_id == "@testchan"


@respx.mock
async def test_resolve_channel_null(client):
    respx.post("http://test/api/admin/bot/channels/resolve").mock(
        return_value=httpx.Response(200, text="null", headers={"content-type": "application/json"})
    )
    assert await client.resolve_channel(1) is None


# ── create_post_log ─────────────────────────────────────────────────


@respx.mock
async def test_create_post_log(client):
    respx.post("http://test/api/admin/bot/post-logs").mock(
        return_value=httpx.Response(200, json={"id": 1})
    )
    result = await client.create_post_log(
        artwork_id=1, channel_id="@testchan", message_id="42", message_link="https://t.me/c/1/42"
    )
    assert result == {"id": 1}


# ── pop_queue_item ──────────────────────────────────────────────────


@respx.mock
async def test_pop_queue_item(client):
    respx.post("http://test/api/admin/bot/queue/pop").mock(
        return_value=httpx.Response(200, json=_QUEUE_ITEM_RESP)
    )
    item = await client.pop_queue_item()
    assert item is not None
    assert isinstance(item, QueueItem)
    assert item.id == 5


@respx.mock
async def test_pop_queue_item_empty(client):
    respx.post("http://test/api/admin/bot/queue/pop").mock(
        return_value=httpx.Response(200, text="null", headers={"content-type": "application/json"})
    )
    assert await client.pop_queue_item() is None


# ── mark_queue_done / failed ────────────────────────────────────────


@respx.mock
async def test_mark_queue_done(client):
    respx.post("http://test/api/admin/bot/queue/5/done").mock(
        return_value=httpx.Response(200, json={})
    )
    await client.mark_queue_done(5)  # 不应抛出异常


@respx.mock
async def test_mark_queue_failed(client):
    respx.post("http://test/api/admin/bot/queue/5/failed").mock(
        return_value=httpx.Response(200, json={})
    )
    await client.mark_queue_failed(5, error="test error")


# ── check_admin ─────────────────────────────────────────────────────


@respx.mock
async def test_check_admin(client):
    respx.get("http://test/api/auth/check-admin").mock(
        return_value=httpx.Response(200, json={"is_admin": True})
    )
    assert await client.check_admin(12345) is True


# ── get_bot_settings ────────────────────────────────────────────────


@respx.mock
async def test_get_bot_settings(client):
    respx.get("http://test/api/admin/bot/settings").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"key": "queue_enabled", "value": "true"},
                {"key": "queue_interval_minutes", "value": "60"},
            ],
        )
    )
    settings = await client.get_bot_settings()
    assert settings == {"queue_enabled": "true", "queue_interval_minutes": "60"}


# ── download_image ──────────────────────────────────────────────────


@respx.mock
async def test_download_image(client):
    image_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * 50
    respx.get("http://test/images/1.jpg").mock(
        return_value=httpx.Response(200, content=image_bytes)
    )
    data = await client.download_image("http://test/images/1.jpg")
    assert data == image_bytes


# ── ArtworkData 单元测试 ────────────────────────────────────────────


def test_artwork_data_from_response():
    art = ArtworkData.from_response(_ARTWORK_RESP)
    assert art.id == 1
    assert art.platform == "pixiv"
    assert art.title_zh == "夕阳"
    assert len(art.images) == 1
    assert art.images[0].url_raw == "https://img.example/raw.png"
    assert art.images[0].width == 1920
    assert len(art.tags) == 2


def test_artwork_data_properties():
    art = ArtworkData.from_response(_ARTWORK_RESP)
    assert art.tag_names == ["landscape", "sunset"]
    assert art.image_urls == ["https://img.example/original.jpg"]
    assert art.raw_image_urls == ["https://img.example/raw.png"]
