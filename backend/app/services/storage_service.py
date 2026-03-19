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
from urllib.parse import urlparse

import httpx
import imagehash
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.artwork import Artwork, ArtworkImage

logger = logging.getLogger(__name__)

# Reusable HTTP client for downloading images
_http_client: httpx.AsyncClient | None = None


# Domain → Referer mapping for hotlink-protected image CDNs
_REFERER_MAP: dict[str, str] = {
    "i.pximg.net": "https://www.pixiv.net/",
    "pbs.twimg.com": "https://x.com/",
}


def _get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(
            follow_redirects=True,
            timeout=60.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
            },
        )
    return _http_client


def _download_headers(url: str) -> dict[str, str]:
    """Build per-request headers (e.g. Referer) based on image URL domain."""
    host = urlparse(url).hostname or ""
    headers: dict[str, str] = {}
    for domain, referer in _REFERER_MAP.items():
        if host == domain or host.endswith(f".{domain}"):
            headers["Referer"] = referer
            break
    return headers


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


async def _save_local(key: str, data: bytes) -> tuple[str, str]:
    """Save bytes to local filesystem. Returns (file_path, public_url)."""
    path = Path(settings.storage_local_path) / key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    public_url = f"{settings.backend_url.rstrip('/')}/images/{key}"
    return str(path), public_url


async def _save_s3(key: str, data: bytes) -> tuple[str, str]:
    """Upload bytes to S3-compatible storage. Returns (s3_key, public_url)."""
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
        public_url = f"{settings.s3_public_url.rstrip('/')}/{key}"
    else:
        public_url = f"{settings.s3_endpoint}/{settings.s3_bucket}/{key}"
    return key, public_url


async def _save(key: str, data: bytes) -> tuple[str, str]:
    """Save to configured backend. Returns (storage_path, public_url)."""
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
    total = len(artwork.images)
    processed = 0
    skipped = 0
    failed = 0

    logger.info(
        "Artwork #%d (%s/%s): starting image processing (%d images)",
        artwork.id, artwork.platform, artwork.pid, total,
    )

    for img_record in artwork.images:
        if not img_record.url_original:
            skipped += 1
            continue

        if img_record.storage_path:
            skipped += 1
            logger.debug(
                "  [%d/%d] page %d — already processed, skipping",
                skipped + processed, total, img_record.page_index,
            )
            continue

        try:
            await _process_single_image(client, artwork, img_record)
            processed += 1
            logger.info(
                "  [%d/%d] page %d — OK (%dx%d, %s)",
                processed + skipped, total, img_record.page_index,
                img_record.width, img_record.height,
                _human_size(img_record.file_size),
            )
        except Exception:
            failed += 1
            logger.warning(
                "  [%d/%d] page %d — FAILED (url: %s)",
                processed + skipped + failed, total,
                img_record.page_index, img_record.url_original,
                exc_info=True,
            )

    await db.commit()
    logger.info(
        "Artwork #%d: done — %d processed, %d skipped, %d failed",
        artwork.id, processed, skipped, failed,
    )


def _human_size(size_bytes: int) -> str:
    """Format bytes to human-readable string."""
    for unit in ("B", "KB", "MB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024  # type: ignore[assignment]
    return f"{size_bytes:.1f}GB"


async def _process_single_image(
    client: httpx.AsyncClient,
    artwork: Artwork,
    img_record: ArtworkImage,
) -> None:
    """Download, process, and store a single image."""
    logger.info(
        "  Downloading page %d: %s",
        img_record.page_index, img_record.url_original,
    )
    resp = await client.get(img_record.url_original, headers=_download_headers(img_record.url_original))
    resp.raise_for_status()
    raw_data = resp.content
    logger.info(
        "  Downloaded %s (%s)", img_record.url_original, _human_size(len(raw_data)),
    )

    # Process original → WebP
    original_key = _storage_key(artwork.platform, artwork.pid, "original", img_record.page_index)
    original_bytes, width, height = _process_image(raw_data)
    original_storage_path, original_url = await _save(original_key, original_bytes)
    logger.debug(
        "  Saved original: %s (%dx%d, %s → %s)",
        original_key, width, height, _human_size(len(raw_data)), _human_size(len(original_bytes)),
    )

    # Process thumbnail
    thumb_key = _storage_key(artwork.platform, artwork.pid, "thumb", img_record.page_index)
    thumb_bytes, thumb_w, thumb_h = _process_image(raw_data, max_edge=settings.thumb_max_edge)
    _, thumb_url = await _save(thumb_key, thumb_bytes)
    logger.debug(
        "  Saved thumb: %s (%dx%d, %s)",
        thumb_key, thumb_w, thumb_h, _human_size(len(thumb_bytes)),
    )

    # Compute perceptual hash
    img_obj = Image.open(io.BytesIO(raw_data))
    phash_value = str(imagehash.phash(img_obj))
    logger.debug("  pHash: %s", phash_value)

    # Update DB record — URLs point to backend serving endpoints
    img_record.storage_path = original_storage_path
    img_record.url_original = original_url
    img_record.url_thumb = thumb_url
    img_record.width = width
    img_record.height = height
    img_record.file_size = len(original_bytes)
    img_record.file_name = f"{img_record.page_index}.webp"
    img_record.phash = phash_value
