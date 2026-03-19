"""提供本地存储的图片服务。

当 storage_backend 为 'local' 时，从本地 uploads 目录提供图片。
当使用 S3 时，图片通过其公开 URL 直接访问（无需代理）。
"""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import settings

router = APIRouter()


@router.get("/{path:path}")
async def serve_image(path: str) -> FileResponse:
    """从本地存储提供图片文件。"""
    if settings.storage_backend != "local":
        raise HTTPException(404, "使用 S3 时本地图片服务已禁用")

    file_path = Path(settings.storage_local_path) / path
    if not file_path.is_file():
        raise HTTPException(404, "图片不存在")

    # 防止路径穿越
    try:
        file_path.resolve().relative_to(Path(settings.storage_local_path).resolve())
    except ValueError:
        raise HTTPException(403, "禁止访问")

    return FileResponse(file_path, media_type="image/webp")
