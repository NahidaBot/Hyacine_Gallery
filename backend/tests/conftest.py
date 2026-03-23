"""Shared test fixtures for backend tests."""

from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — 确保所有模型注册到 Base.metadata
from app.database import Base
from app.schemas.artwork import ArtworkCreate
from app.schemas.author import AuthorCreate
from app.schemas.bot import BotChannelCreate, BotPostLogCreate
from app.schemas.tag import TagCreate


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession]:
    """内存 SQLite 异步会话，每个测试独立。"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine.sync_engine, "connect")
    def _set_pragma(conn, _record):
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        from app.services.tag_service import seed_default_tag_types

        await seed_default_tag_types(session)
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def app_client(db: AsyncSession) -> AsyncGenerator:
    """FastAPI TestClient with overridden DB and auth dependencies."""
    import httpx
    from httpx import ASGITransport

    from app.api.dependencies import get_session, require_admin, require_owner
    from app.main import app

    async def _override_session():
        yield db

    async def _noop():
        return None

    app.dependency_overrides[get_session] = _override_session
    app.dependency_overrides[require_admin] = _noop
    app.dependency_overrides[require_owner] = _noop

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
async def sample_artwork(db: AsyncSession):
    """创建一个包含 1 图片、1 来源、2 标签的样本作品。"""
    from app.services.artwork_service import create_artwork

    data = ArtworkCreate(
        platform="pixiv",
        pid="12345",
        title="Test Artwork",
        author="Test Author",
        author_id="author_001",
        source_url="https://pixiv.net/artworks/12345",
        page_count=1,
        is_nsfw=False,
        is_ai=False,
        image_urls=["https://i.pximg.net/img/12345_p0.jpg"],
        tags=["landscape", "sky"],
    )
    return await create_artwork(db, data)


@pytest.fixture
async def sample_tag(db: AsyncSession):
    """创建一个样本标签。"""
    from app.services.tag_service import create_tag

    return await create_tag(db, TagCreate(name="test_tag", type="general"))


@pytest.fixture
async def sample_author(db: AsyncSession):
    """创建一个样本作者。"""
    from app.services.author_service import create_author

    return await create_author(
        db, AuthorCreate(name="Pixiv Artist", platform="pixiv", platform_uid="uid_001")
    )


@pytest.fixture
async def sample_channel(db: AsyncSession):
    """创建一个样本 Bot 频道。"""
    from app.services.bot_service import create_channel

    return await create_channel(
        db,
        BotChannelCreate(
            platform="telegram",
            channel_id="-1001234567890",
            name="Test Channel",
            is_default=True,
            priority=0,
            conditions={},
            enabled=True,
        ),
    )


@pytest.fixture
async def sample_post_log(db: AsyncSession, sample_artwork):
    """创建一个样本发布日志。"""
    from app.services.bot_service import create_post_log

    return await create_post_log(
        db,
        BotPostLogCreate(
            artwork_id=sample_artwork.id,
            bot_platform="telegram",
            channel_id="-1001234567890",
            message_id="999",
            posted_by="test_user",
        ),
    )
