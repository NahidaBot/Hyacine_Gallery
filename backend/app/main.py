import asyncio
import contextlib
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.images import router as images_router
from app.api.router import api_router
from app.database import async_session
from app.services.cleanup_service import raw_cleanup_loop
from app.services.tag_service import seed_default_tag_types


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # 启动时初始化默认标签类型
    async with async_session() as db:
        await seed_default_tag_types(db)
    # 启动 raw 文件过期清理后台任务
    cleanup_task = asyncio.create_task(raw_cleanup_loop())
    yield
    # 关闭时取消清理任务
    cleanup_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await cleanup_task


app = FastAPI(
    title="Hyacine Gallery",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")
app.include_router(images_router, prefix="/images", tags=["images"])


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
