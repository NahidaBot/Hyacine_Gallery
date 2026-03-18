"""Serve locally stored images.

When storage_backend is 'local', images are served from the local uploads directory.
When using S3, images are served directly via their public URL (no proxy needed).
"""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import settings

router = APIRouter()


@router.get("/{path:path}")
async def serve_image(path: str) -> FileResponse:
    """Serve an image file from local storage."""
    if settings.storage_backend != "local":
        raise HTTPException(404, "Local image serving is disabled when using S3")

    file_path = Path(settings.storage_local_path) / path
    if not file_path.is_file():
        raise HTTPException(404, "Image not found")

    # Prevent path traversal
    try:
        file_path.resolve().relative_to(Path(settings.storage_local_path).resolve())
    except ValueError:
        raise HTTPException(403, "Forbidden")

    return FileResponse(file_path, media_type="image/webp")
