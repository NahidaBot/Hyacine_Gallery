"""raw 原始文件过期清理服务。

定期扫描 artwork_images 中 raw_expires_at 已过期的记录，
删除对应的物理文件（本地或 S3），并清空相关字段。
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session
from app.models.artwork import ArtworkImage

logger = logging.getLogger(__name__)


def _delete_raw_file(storage_path: str) -> None:
    """删除 raw 文件（本地或 S3）。失败时仅记录警告，不抛出异常。"""
    if not storage_path:
        return
    if settings.storage_backend == "local":
        path = Path(storage_path)
        if path.exists():
            path.unlink()
    else:
        try:
            import boto3
            from botocore.config import Config as BotoConfig

            s3 = boto3.client(
                "s3",
                endpoint_url=settings.s3_endpoint or None,
                aws_access_key_id=settings.s3_access_key,
                aws_secret_access_key=settings.s3_secret_key,
                region_name=settings.s3_region or None,
                config=BotoConfig(signature_version="s3v4"),
            )
            s3.delete_object(Bucket=settings.s3_bucket, Key=storage_path)
        except Exception:
            logger.warning("删除 S3 raw 文件失败: %s", storage_path, exc_info=True)


async def cleanup_expired_raw_files(db: AsyncSession) -> int:
    """清理所有已过期的 raw 文件。返回处理的记录数。"""
    now = datetime.now(UTC)
    result = await db.execute(
        select(ArtworkImage).where(
            ArtworkImage.raw_expires_at.is_not(None),  # type: ignore[union-attr]
            ArtworkImage.raw_expires_at <= now,  # type: ignore[operator]
            ArtworkImage.storage_path_raw != "",
        )
    )
    expired = result.scalars().all()
    for img in expired:
        try:
            _delete_raw_file(img.storage_path_raw)
        except Exception:
            logger.warning("删除 raw 文件失败: %s", img.storage_path_raw, exc_info=True)
        img.storage_path_raw = ""
        img.url_raw = ""
        img.raw_expires_at = None
    if expired:
        await db.commit()
    return len(expired)


async def raw_cleanup_loop() -> None:
    """每小时执行一次过期清理，在 lifespan 中以 asyncio.create_task 启动。"""
    while True:
        try:
            async with async_session() as db:
                n = await cleanup_expired_raw_files(db)
            if n:
                logger.info("raw 文件清理完成，已删除 %d 条记录", n)
        except Exception:
            logger.exception("raw 文件清理循环出错")
        await asyncio.sleep(3600)
