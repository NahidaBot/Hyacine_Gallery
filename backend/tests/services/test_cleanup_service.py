"""cleanup_service 单元测试。"""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.artwork import ArtworkCreate
from app.services.artwork_service import create_artwork
from app.services.cleanup_service import (
    cleanup_expired_raw_files,
    cleanup_orphan_images,
    find_orphan_images,
)


async def test_cleanup_expired_raw_files(db: AsyncSession):
    """过期的 raw 文件应被清理，字段应被清空。"""
    artwork = await create_artwork(
        db,
        ArtworkCreate(
            platform="pixiv",
            pid="cleanup1",
            title="Cleanup Test",
            image_urls=["https://example.com/1.jpg"],
        ),
    )
    img = artwork.images[0]
    img.storage_path_raw = "raw/test.jpg"
    img.url_raw = "http://example.com/raw/test.jpg"
    img.raw_expires_at = datetime.now(UTC) - timedelta(hours=1)
    await db.commit()

    with patch("app.services.cleanup_service._delete_raw_file") as mock_delete:
        count = await cleanup_expired_raw_files(db)

    assert count == 1
    mock_delete.assert_called_once_with("raw/test.jpg")
    await db.refresh(img)
    assert img.storage_path_raw == ""
    assert img.url_raw == ""
    assert img.raw_expires_at is None


async def test_cleanup_expired_raw_files_none(db: AsyncSession):
    """无过期记录时应返回 0。"""
    count = await cleanup_expired_raw_files(db)
    assert count == 0


async def test_find_orphan_images(db: AsyncSession):
    """storage_path 指向不存在文件的记录应被发现。"""
    artwork = await create_artwork(
        db,
        ArtworkCreate(
            platform="pixiv",
            pid="orphan1",
            title="Orphan Test",
            image_urls=["https://example.com/1.jpg"],
        ),
    )
    img = artwork.images[0]
    img.storage_path = "some/path.webp"
    await db.commit()

    with patch("app.services.cleanup_service._file_exists", return_value=False):
        orphans = await find_orphan_images(db)

    assert len(orphans) == 1
    assert orphans[0]["id"] == img.id
    assert orphans[0]["storage_path"] == "some/path.webp"


async def test_cleanup_orphan_images(db: AsyncSession):
    """悬空图片记录的 storage_path 和 url_thumb 应被清空。"""
    artwork = await create_artwork(
        db,
        ArtworkCreate(
            platform="pixiv",
            pid="orphan2",
            title="Orphan Cleanup Test",
            image_urls=["https://example.com/1.jpg"],
        ),
    )
    img = artwork.images[0]
    img.storage_path = "some/path.webp"
    img.url_thumb = "http://example.com/thumb.webp"
    await db.commit()

    with patch("app.services.cleanup_service._file_exists", return_value=False):
        count = await cleanup_orphan_images(db)

    assert count == 1
    await db.refresh(img)
    assert img.storage_path == ""
    assert img.url_thumb == ""


async def test_cleanup_orphan_images_with_ids(db: AsyncSession):
    """指定 image_ids 时应只清理指定的记录。"""
    artwork = await create_artwork(
        db,
        ArtworkCreate(
            platform="pixiv",
            pid="orphan3",
            title="Orphan IDs Test",
            image_urls=["https://example.com/1.jpg", "https://example.com/2.jpg"],
        ),
    )
    img1 = artwork.images[0]
    img2 = artwork.images[1]
    img1.storage_path = "path1.webp"
    img1.url_thumb = "http://thumb1"
    img2.storage_path = "path2.webp"
    img2.url_thumb = "http://thumb2"
    await db.commit()

    count = await cleanup_orphan_images(db, image_ids=[img1.id])
    assert count == 1
    await db.refresh(img1)
    await db.refresh(img2)
    assert img1.storage_path == ""
    assert img2.storage_path == "path2.webp"


async def test_find_orphan_images_none(db: AsyncSession):
    """所有文件都存在时应返回空列表。"""
    artwork = await create_artwork(
        db,
        ArtworkCreate(
            platform="pixiv",
            pid="no_orphan",
            title="No Orphan",
            image_urls=["https://example.com/1.jpg"],
        ),
    )
    artwork.images[0].storage_path = "exists.webp"
    await db.commit()

    with patch("app.services.cleanup_service._file_exists", return_value=True):
        orphans = await find_orphan_images(db)
    assert orphans == []


def test_delete_raw_file_local(tmp_path, monkeypatch):
    """本地存储应删除文件。"""
    from app.services.cleanup_service import _delete_raw_file

    monkeypatch.setattr("app.services.cleanup_service.settings.storage_backend", "local")
    f = tmp_path / "test.jpg"
    f.write_bytes(b"data")
    assert f.exists()
    _delete_raw_file(str(f))
    assert not f.exists()


def test_delete_raw_file_local_missing(monkeypatch):
    """不存在的本地文件不应抛异常。"""
    from app.services.cleanup_service import _delete_raw_file

    monkeypatch.setattr("app.services.cleanup_service.settings.storage_backend", "local")
    _delete_raw_file("/nonexistent/path/test.jpg")  # 不抛异常


def test_delete_raw_file_empty():
    """空路径不应执行任何操作。"""
    from app.services.cleanup_service import _delete_raw_file

    _delete_raw_file("")  # 不抛异常


def test_file_exists_local(tmp_path, monkeypatch):
    """本地文件存在检查。"""
    from app.services.cleanup_service import _file_exists

    monkeypatch.setattr("app.services.cleanup_service.settings.storage_backend", "local")
    f = tmp_path / "test.webp"
    f.write_bytes(b"data")
    assert _file_exists(str(f)) is True
    assert _file_exists(str(tmp_path / "nonexistent.webp")) is False
