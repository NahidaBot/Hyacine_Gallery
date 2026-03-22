"""图片下载、处理和存储服务。

下载来源 URL 的图片，转换为 WebP（可配置质量），
生成缩略图（可配置最大边长），存储到本地文件系统或 S3。

存储布局:
    <platform>/<pid>/original/<page_index>.webp   — WebP 压缩的原图
    <platform>/<pid>/thumb/<page_index>.webp       — 缩略图（长边 ≤ thumb_max_edge）
    <platform>/<pid>/raw/<page_index>.<ext>        — 原始文件（TTL 控制，默认保留 7 天）
"""

from __future__ import annotations

import asyncio
import io
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

import httpx
import imagehash
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.artwork import Artwork, ArtworkImage

logger = logging.getLogger(__name__)

# 可复用的 HTTP 客户端，用于下载图片
_http_client: httpx.AsyncClient | None = None


# 域名 → Referer 映射，用于防盗链的图片 CDN
_REFERER_MAP: dict[str, str] = {
    "i.pximg.net": "https://www.pixiv.net/",
    "pbs.twimg.com": "https://x.com/",
    "upload-bbs.miyoushe.com": "https://www.miyoushe.com/",
    "upload-os-bbs.hoyolab.com": "https://www.hoyolab.com/",
    "act-upload.mihoyo.com": "https://www.miyoushe.com/",
    "i0.hdslb.com": "https://www.bilibili.com/",
    "i1.hdslb.com": "https://www.bilibili.com/",
    "i2.hdslb.com": "https://www.bilibili.com/",
}


def _get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(
            follow_redirects=True,
            timeout=5.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
            },
        )
    return _http_client


def _download_headers(url: str) -> dict[str, str]:
    """根据图片 URL 域名构建请求头（如 Referer）。"""
    host = urlparse(url).hostname or ""
    headers: dict[str, str] = {}
    for domain, referer in _REFERER_MAP.items():
        if host == domain or host.endswith(f".{domain}"):
            headers["Referer"] = referer
            break
    return headers


async def download_image_bytes(url: str) -> bytes:
    """下载图片并返回原始字节。用于 AI 标签建议等需要图片数据的场景。"""
    client = _get_http_client()
    headers = _download_headers(url)
    resp = await client.get(url, headers=headers)
    resp.raise_for_status()
    return resp.content


def _storage_key(platform: str, pid: str, variant: str, page_index: int) -> str:
    """构建存储键，如 'pixiv/12345/original/0.webp'。"""
    return f"{platform}/{pid}/{variant}/{page_index}.webp"


def _raw_storage_key(platform: str, pid: str, page_index: int, ext: str) -> str:
    """构建 raw 存储键，如 'pixiv/12345/raw/0.jpg'。"""
    return f"{platform}/{pid}/raw/{page_index}.{ext}"


def _detect_ext(data: bytes) -> str:
    """从魔术字节识别图片格式，回退到 bin。"""
    if data[:3] == b"\xff\xd8\xff":
        return "jpg"
    if data[:4] == b"\x89PNG":
        return "png"
    if data[8:12] == b"WEBP":
        return "webp"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    return "bin"


def _process_image(
    data: bytes,
    *,
    quality: int = settings.webp_quality,
    max_edge: int | None = None,
) -> tuple[bytes, int, int]:
    """将图片数据转换为 WebP，可选缩放。返回 (webp_bytes, width, height)。"""
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


# ── 存储后端 ─────────────────────────────────────────────────────


async def _save_local(key: str, data: bytes) -> tuple[str, str]:
    """保存字节到本地文件系统。返回 (file_path, public_url)。"""
    path = Path(settings.storage_local_path) / key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    public_url = f"{settings.backend_url.rstrip('/')}/images/{key}"
    return str(path), public_url


async def _save_s3(key: str, data: bytes, content_type: str = "image/webp") -> tuple[str, str]:
    """上传字节到 S3 兼容存储。返回 (s3_key, public_url)。"""
    try:
        import boto3
        from botocore.config import Config as BotoConfig
    except ImportError as e:
        raise RuntimeError("S3 存储需要 boto3") from e

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
        ContentType=content_type,
    )

    if settings.s3_public_url:
        public_url = f"{settings.s3_public_url.rstrip('/')}/{key}"
    else:
        public_url = f"{settings.s3_endpoint}/{settings.s3_bucket}/{key}"
    return key, public_url


async def _save(key: str, data: bytes, content_type: str = "image/webp") -> tuple[str, str]:
    """保存到已配置的后端。返回 (storage_path, public_url)。"""
    if settings.storage_backend == "s3":
        return await _save_s3(key, data, content_type)
    return await _save_local(key, data)


# ── 公开 API ─────────────────────────────────────────────────────


async def download_and_store_images(
    db: AsyncSession,
    artwork: Artwork,
) -> None:
    """下载作品的所有图片，处理后更新数据库记录。

    对每个 ArtworkImage:
      - 下载原始 URL
      - 转换为 WebP（80% 质量）→ 存储为 'original'
      - 生成缩略图（长边 ≤ thumb_max_edge）→ 存储为 'thumb'
      - 更新 width、height、file_size、file_name、storage_path、url_thumb
    """
    client = _get_http_client()
    total = len(artwork.images)
    processed = 0
    skipped = 0
    failed = 0

    logger.info(
        "作品 #%d (%s/%s): 开始图片处理（共 %d 张）",
        artwork.id,
        artwork.platform,
        artwork.pid,
        total,
    )

    for img_record in artwork.images:
        if not img_record.url_original:
            skipped += 1
            continue

        if img_record.storage_path:
            skipped += 1
            logger.debug(
                "  [%d/%d] 第 %d 页 — 已处理，跳过",
                skipped + processed,
                total,
                img_record.page_index,
            )
            continue

        try:
            await _process_single_image(client, artwork, img_record)
            processed += 1
            logger.info(
                "  [%d/%d] 第 %d 页 — 成功 (%dx%d, %s)",
                processed + skipped,
                total,
                img_record.page_index,
                img_record.width,
                img_record.height,
                _human_size(img_record.file_size),
            )
        except Exception:
            failed += 1
            logger.warning(
                "  [%d/%d] 第 %d 页 — 失败 (url: %s)",
                processed + skipped + failed,
                total,
                img_record.page_index,
                img_record.url_original,
                exc_info=True,
            )

    await db.commit()
    logger.info(
        "作品 #%d: 完成 — %d 已处理, %d 已跳过, %d 失败",
        artwork.id,
        processed,
        skipped,
        failed,
    )


def _human_size(size_bytes: int) -> str:
    """将字节数格式化为可读字符串。"""
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
    """下载、处理并存储单张图片。"""
    logger.info(
        "  正在下载第 %d 页: %s",
        img_record.page_index,
        img_record.url_original,
    )
    _RETRIES = 10
    raw_data: bytes = b""
    for attempt in range(_RETRIES):
        try:
            resp = await client.get(
                img_record.url_original,
                headers=_download_headers(img_record.url_original),
            )
            resp.raise_for_status()
            raw_data = resp.content
            break
        except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError) as e:
            if attempt == _RETRIES - 1:
                raise
            wait = 2**attempt
            logger.warning("图片下载失败（第 %d 次），%.0fs 后重试: %s", attempt + 1, wait, e)
            await asyncio.sleep(wait)
    logger.info(
        "  已下载 %s (%s)",
        img_record.url_original,
        _human_size(len(raw_data)),
    )

    # 存储原始文件（TTL 控制）
    if settings.raw_ttl_days > 0:
        ext = _detect_ext(raw_data)
        raw_key = _raw_storage_key(artwork.platform, artwork.pid, img_record.page_index, ext)
        mime = f"image/{ext}" if ext != "bin" else "application/octet-stream"
        raw_storage_path, raw_url = await _save(raw_key, raw_data, content_type=mime)
        img_record.storage_path_raw = raw_storage_path
        img_record.url_raw = raw_url
        img_record.raw_expires_at = datetime.now(UTC) + timedelta(days=settings.raw_ttl_days)
        logger.debug(
            "  已保存原始文件: %s (%s, 过期: %s)",
            raw_key,
            _human_size(len(raw_data)),
            img_record.raw_expires_at.date(),
        )

    # 处理原图 → WebP
    original_key = _storage_key(artwork.platform, artwork.pid, "original", img_record.page_index)
    original_bytes, width, height = _process_image(raw_data)
    original_storage_path, original_url = await _save(original_key, original_bytes)
    logger.debug(
        "  已保存原图: %s (%dx%d, %s → %s)",
        original_key,
        width,
        height,
        _human_size(len(raw_data)),
        _human_size(len(original_bytes)),
    )

    # 处理缩略图
    thumb_key = _storage_key(artwork.platform, artwork.pid, "thumb", img_record.page_index)
    thumb_bytes, thumb_w, thumb_h = _process_image(raw_data, max_edge=settings.thumb_max_edge)
    _, thumb_url = await _save(thumb_key, thumb_bytes)
    logger.debug(
        "  已保存缩略图: %s (%dx%d, %s)",
        thumb_key,
        thumb_w,
        thumb_h,
        _human_size(len(thumb_bytes)),
    )

    # 计算感知哈希
    img_obj = Image.open(io.BytesIO(raw_data))
    phash_value = str(imagehash.phash(img_obj))
    logger.debug("  pHash: %s", phash_value)

    # 更新数据库记录 — URL 指向后端服务端点
    img_record.storage_path = original_storage_path
    img_record.url_original = original_url
    img_record.url_thumb = thumb_url
    img_record.width = width
    img_record.height = height
    img_record.file_size = len(original_bytes)
    img_record.file_name = f"{img_record.page_index}.webp"
    img_record.phash = phash_value
