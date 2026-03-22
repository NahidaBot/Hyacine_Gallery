from fastapi import APIRouter

from app.api.artworks import router as artworks_router
from app.api.auth import router as auth_router
from app.api.authors import router as authors_router
from app.api.bot import router as bot_router
from app.api.tags import router as tags_router
from app.api.admin import router as admin_router
from app.api.users import router as users_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(artworks_router, prefix="/artworks", tags=["artworks"])
api_router.include_router(authors_router, prefix="/authors", tags=["authors"])
api_router.include_router(tags_router, prefix="/tags", tags=["tags"])
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])
api_router.include_router(bot_router, prefix="/admin/bot", tags=["bot"])
api_router.include_router(users_router, prefix="/admin/users", tags=["users"])
