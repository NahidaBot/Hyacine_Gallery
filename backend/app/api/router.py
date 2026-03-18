from fastapi import APIRouter

from app.api.artworks import router as artworks_router
from app.api.tags import router as tags_router
from app.api.admin import router as admin_router

api_router = APIRouter()
api_router.include_router(artworks_router, prefix="/artworks", tags=["artworks"])
api_router.include_router(tags_router, prefix="/tags", tags=["tags"])
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])
