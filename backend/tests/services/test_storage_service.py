"""storage_service 单元测试 — 测试 header 构建和格式检测。"""

from pathlib import Path

from app.services.storage_service import _detect_ext, _download_headers

# ── _download_headers ──


async def test_download_headers_pixiv():
    """Pixiv 图片 CDN 应带 pixiv.net Referer。"""
    headers = _download_headers("https://i.pximg.net/img/12345_p0.jpg")
    assert headers["Referer"] == "https://www.pixiv.net/"


async def test_download_headers_twitter():
    """Twitter 图片 CDN 应带 x.com Referer。"""
    headers = _download_headers("https://pbs.twimg.com/media/abc.jpg")
    # _REFERER_MAP 中 pbs.twimg.com 对应 https://x.com/
    assert headers["Referer"] == "https://x.com/"


async def test_download_headers_bilibili():
    """Bilibili 图片 CDN 应带 bilibili.com Referer。"""
    headers = _download_headers("https://i0.hdslb.com/bfs/article/abc.jpg")
    assert headers["Referer"] == "https://www.bilibili.com/"


async def test_download_headers_unknown():
    """未知域名不应携带 Referer。"""
    headers = _download_headers("https://example.com/image.jpg")
    assert "Referer" not in headers


# ── _detect_ext ──


async def test_detect_ext_jpg():
    data = b"\xff\xd8\xff\xe0" + b"\x00" * 100
    assert _detect_ext(data) == "jpg"


async def test_detect_ext_png():
    data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
    assert _detect_ext(data) == "png"


async def test_detect_ext_webp():
    data = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 100
    assert _detect_ext(data) == "webp"


async def test_detect_ext_gif():
    data = b"GIF89a" + b"\x00" * 100
    assert _detect_ext(data) == "gif"


async def test_detect_ext_unknown():
    data = b"\x00\x01\x02\x03\x04\x05" + b"\x00" * 100
    assert _detect_ext(data) == "bin"


# ── _storage_key / _raw_storage_key ──


def test_storage_key():
    from app.services.storage_service import _storage_key

    assert _storage_key("pixiv", "123", "original", 0) == "pixiv/123/original/0.webp"
    assert _storage_key("twitter", "456", "thumb", 2) == "twitter/456/thumb/2.webp"


def test_raw_storage_key():
    from app.services.storage_service import _raw_storage_key

    assert _raw_storage_key("pixiv", "123", 0, "jpg") == "pixiv/123/raw/0.jpg"
    assert _raw_storage_key("pixiv", "123", 1, "png") == "pixiv/123/raw/1.png"


# ── _process_image ──


def test_process_image_webp():
    """应将 RGB 图片转换为 WebP 并返回尺寸。"""
    import io

    from PIL import Image

    from app.services.storage_service import _process_image

    img = Image.new("RGB", (100, 200), color="red")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    data = buf.getvalue()

    webp_bytes, w, h = _process_image(data)
    assert w == 100
    assert h == 200
    assert len(webp_bytes) > 0
    # 验证输出是 WebP 格式
    assert _detect_ext(webp_bytes) == "webp"


def test_process_image_with_max_edge():
    """当图片超过 max_edge 时应缩放。"""
    import io

    from PIL import Image

    from app.services.storage_service import _process_image

    img = Image.new("RGB", (2000, 1000), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    data = buf.getvalue()

    webp_bytes, w, h = _process_image(data, max_edge=500)
    assert max(w, h) <= 500


def test_process_image_no_scale():
    """当图片小于 max_edge 时不缩放。"""
    import io

    from PIL import Image

    from app.services.storage_service import _process_image

    img = Image.new("RGB", (100, 50), color="green")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    data = buf.getvalue()

    webp_bytes, w, h = _process_image(data, max_edge=500)
    assert w == 100
    assert h == 50


def test_process_image_rgba():
    """应正确处理 RGBA 模式图片。"""
    import io

    from PIL import Image

    from app.services.storage_service import _process_image

    img = Image.new("RGBA", (50, 50), color=(255, 0, 0, 128))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    data = buf.getvalue()

    webp_bytes, w, h = _process_image(data)
    assert w == 50
    assert h == 50


# ── _save_local ──


async def test_save_local(tmp_path, monkeypatch):
    """本地存储应写入文件并返回正确 URL。"""
    from app.services.storage_service import _save_local

    monkeypatch.setattr("app.services.storage_service.settings.storage_local_path", str(tmp_path))
    monkeypatch.setattr("app.services.storage_service.settings.backend_url", "http://test:8000")

    file_path, public_url = await _save_local("pixiv/123/original/0.webp", b"fake_webp_data")
    assert Path(file_path).exists()
    assert Path(file_path).read_bytes() == b"fake_webp_data"
    assert public_url == "http://test:8000/images/pixiv/123/original/0.webp"


# ── _human_size ──


def test_human_size():
    from app.services.storage_service import _human_size

    assert _human_size(0) == "0.0B"
    assert _human_size(500) == "500.0B"
    assert _human_size(1024) == "1.0KB"
    assert _human_size(1048576) == "1.0MB"


# ── download_and_store_images ──


async def test_download_and_store_skips_processed(db, sample_artwork, monkeypatch):
    """已有 storage_path 的图片应被跳过。"""
    from app.services.storage_service import download_and_store_images

    sample_artwork.images[0].storage_path = "already/stored/path.webp"
    await db.commit()

    # 如果图片不被跳过，会尝试 HTTP 下载并失败
    # 跳过的图片不会触发任何下载
    await download_and_store_images(db, sample_artwork)
    # 验证 storage_path 未被修改
    assert sample_artwork.images[0].storage_path == "already/stored/path.webp"


async def test_download_and_store_skips_no_url(db, monkeypatch):
    """url_original 为空的图片应被跳过。"""
    from app.schemas.artwork import ArtworkCreate
    from app.services.artwork_service import create_artwork
    from app.services.storage_service import download_and_store_images

    artwork = await create_artwork(db, ArtworkCreate(platform="test", pid="nourl", image_urls=[""]))
    # 不应抛异常
    await download_and_store_images(db, artwork)
