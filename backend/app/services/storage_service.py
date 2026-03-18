"""Image download, processing, and storage service.

Downloads images from source URLs, converts to WebP (configurable quality),
generates thumbnails (configurable max edge), and stores to local filesystem or S3.

Storage layout:
    <platform>/<pid>/original/<page_index>.webp   — WebP-compressed original
    <platform>/<pid>/thumb/<page_index>.webp       — Thumbnail (long edge ≤ thumb_max_edge)
"""

from __future__ import annotations

import io
import logging
from pathlib import Path

import httpx
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.artwork import Artwork, ArtworkImage

logger = logging.getLogger(__name__)

# Reusable HTTP client for downloading images
_http_client: httpx.AsyncClient | None = None


def _get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(
            follow_redirects=True,
            timeout=60.0,
            headers={"User-Agent": "HyacineGallery/1.0"},
        )
    return _http_client


def _storage_key(platform: str, pid: str, variant: str, page_index: int) -> str:
    """Build a storage key like 'pixiv/12345/original/0.webp'."""
    return f"{platform}/{pid}/{variant}/{page_index}.webp"


def _process_image(
    data: bytes,
    *,
    quality: int = settings.webp_quality,
    max_edge: int | None = None,
) -> tuple[bytes, int, int]:
    """Convert image data to WebP, optionally resize. Returns (webp_bytes, width, height)."""
    img = Image.open(io.BytesIO(data))
    img = img.convert("RGBA") if img.mode in ("RGBA", "PA", "P") else img.convert("RGB")

    if max_edge is not None:
        w, h = img.size
        long_edge = max(w, h)
        if long_edge > max_edge:
            scale = max_edge / long_edge
            new_w, new_h = int(w * scale), int(h * scale)
            img = img.resize((new_w, new_h), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=quality)
    final_w, final_h = img.size
    return buf.getvalue(), final_w, final_h


# ── Storage backends ─────────────────────────────────────────────


async def _save_local(key: str, data: bytes) -> str:
    """Save bytes to local filesystem. Returns the relative path."""
    path = Path(settings.storage_local_path) / key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return str(path)


async def _save_s3(key: str, data: bytes) -> str:
    """Upload bytes to S3-compatible storage. Returns the public URL."""
    try:
        import boto3
        from botocore.config import Config as BotoConfig
    except ImportError as e:
        raise RuntimeError("boto3 is required for S3 storage: pip install boto3") from e

    s3 = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint or None,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region or None,
        config=BotoConfig(signature_version="s3v4"),
    )
    s3.put_object(
        Bucket=settings.s3_bucket,
        Key=key,
        Body=data,
        ContentType="image/webp",
    )

    if settings.s3_public_url:
        return f"{settings.s3_public_url.rstrip('/')}/{key}"
    return f"{settings.s3_endpoint}/{settings.s3_bucket}/{key}"


async def _save(key: str, data: bytes) -> str:
    """Save to configured backend. Returns path or URL."""
    if settings.storage_backend == "s3":
        return await _save_s3(key, data)
    return await _save_local(key, data)


# ── Public API ───────────────────────────────────────────────────


async def download_and_store_images(
    db: AsyncSession,
    artwork: Artwork,
) -> None:
    """Download all images for an artwork, process them, and update DB records.

    For each ArtworkImage:
      - Downloads the original URL
      - Converts to WebP (80% quality) → stored as 'original'
      - Generates thumbnail (long edge ≤ thumb_max_edge) → stored as 'thumb'
      - Updates width, height, file_size, file_name, storage_path, url_thumb
    """
    client = _get_http_client()

    for img_record in artwork.images:
        if not img_record.url_original:
            continue

        # Skip if already processed
        if img_record.storage_path:
            continue

        try:
            await _process_single_image(client, artwork, img_record)
        except Exception:
            logger.warning(
                "Failed to process image %d for artwork #%d",
                img_record.page_index,
                artwork.id,
                exc_info=True,
            )

    await db.commit()


async def _process_single_image(
    client: httpx.AsyncClient,
    artwork: Artwork,
    img_record: ArtworkImage,
) -> None:
    """Download, process, and store a single image."""
    resp = await client.get(img_record.url_original)
    resp.raise_for_status()
    raw_data = resp.content

    # Process original → WebP
    original_key = _storage_key(artwork.platform, artwork.pid, "original", img_record.page_index)
    original_bytes, width, height = _process_image(raw_data)
    original_path = await _save(original_key, original_bytes)

    # Process thumbnail
    thumb_key = _storage_key(artwork.platform, artwork.pid, "thumb", img_record.page_index)
    thumb_bytes, _, _ = _process_image(raw_data, max_edge=settings.thumb_max_edge)
    thumb_path = await _save(thumb_key, thumb_bytes)

    # Update DB record
    img_record.storage_path = original_path
    img_record.url_thumb = thumb_path
    img_record.width = width
    img_record.height = height
    img_record.file_size = len(original_bytes)
    img_record.file_name = f"{img_record.page_index}.webp"
