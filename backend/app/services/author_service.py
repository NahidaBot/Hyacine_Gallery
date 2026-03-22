from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.author import Author
from app.models.artwork import Artwork
from app.schemas.author import AuthorCreate, AuthorUpdate


async def list_authors(
    db: AsyncSession,
    platform: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[Author], int]:
    """分页获取作者列表，可按平台过滤。"""
    q = select(Author)
    if platform:
        q = q.where(Author.platform == platform)
    q = q.order_by(Author.name)

    count_q = select(func.count()).select_from(q.subquery())
    total: int = (await db.execute(count_q)).scalar_one()

    q = q.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(q)).scalars().all()
    return list(rows), total


async def get_author(db: AsyncSession, author_id: int) -> Author | None:
    return await db.get(Author, author_id)


async def get_author_by_platform_uid(
    db: AsyncSession, platform: str, platform_uid: str
) -> Author | None:
    result = await db.execute(
        select(Author).where(
            Author.platform == platform,
            Author.platform_uid == platform_uid,
        )
    )
    return result.scalar_one_or_none()


async def get_or_create_author(
    db: AsyncSession, platform: str, platform_uid: str, name: str
) -> Author:
    """获取已有作者记录，若不存在则创建。"""
    existing = await get_author_by_platform_uid(db, platform, platform_uid)
    if existing:
        return existing
    author = Author(name=name, platform=platform, platform_uid=platform_uid)
    db.add(author)
    await db.flush()
    return author


async def create_author(db: AsyncSession, data: AuthorCreate) -> Author:
    author = Author(**data.model_dump())
    db.add(author)
    await db.flush()
    return author


async def update_author(
    db: AsyncSession, author_id: int, data: AuthorUpdate
) -> Author | None:
    author = await db.get(Author, author_id)
    if not author:
        return None
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(author, field, value)
    await db.flush()
    return author


async def delete_author(db: AsyncSession, author_id: int) -> bool:
    author = await db.get(Author, author_id)
    if not author:
        return False
    await db.delete(author)
    await db.flush()
    return True


async def get_artworks_by_author(
    db: AsyncSession,
    author_id: int,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Artwork], int]:
    """获取某作者关联的作品列表（通过 author_ref_id）。"""
    q = select(Artwork).where(Artwork.author_ref_id == author_id).order_by(Artwork.created_at.desc())

    count_q = select(func.count()).select_from(q.subquery())
    total: int = (await db.execute(count_q)).scalar_one()

    q = q.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(q)).scalars().all()
    return list(rows), total
