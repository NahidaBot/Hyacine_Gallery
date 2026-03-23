from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.artwork import Artwork
from app.models.author import Author
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
    """获取已有作者记录，若不存在则创建；已存在时同步更新名称。"""
    existing = await get_author_by_platform_uid(db, platform, platform_uid)
    if existing:
        if name and existing.name != name:
            existing.name = name
            await db.flush()
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


async def update_author(db: AsyncSession, author_id: int, data: AuthorUpdate) -> Author | None:
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


async def get_author_by_name(db: AsyncSession, name: str) -> Author | None:
    """按名称查找作者（精确匹配）。"""
    result = await db.execute(select(Author).where(Author.name == name))
    return result.scalars().first()


async def get_artworks_by_author_with_canonical(
    db: AsyncSession,
    author_id: int,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Artwork], int]:
    """获取某作者及其关联作者（共享 canonical_id）的所有作品。"""
    author = await db.get(Author, author_id)
    if not author:
        return [], 0

    canonical = author.canonical_id or author.id
    result = await db.execute(
        select(Author.id).where((Author.id == canonical) | (Author.canonical_id == canonical))
    )
    author_ids = [row[0] for row in result.all()]

    q = (
        select(Artwork)
        .options(
            selectinload(Artwork.images),
            selectinload(Artwork.tags),
            selectinload(Artwork.sources),
        )
        .where(Artwork.author_ref_id.in_(author_ids))
        .order_by(Artwork.created_at.desc())
    )
    count_q = select(func.count()).select_from(
        select(Artwork.id).where(Artwork.author_ref_id.in_(author_ids)).subquery()
    )
    total: int = (await db.execute(count_q)).scalar_one()

    q = q.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(q)).scalars().all()
    return list(rows), total


async def get_artworks_by_author(
    db: AsyncSession,
    author_id: int,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Artwork], int]:
    """获取某作者关联的作品列表（通过 author_ref_id）。"""
    q = (
        select(Artwork)
        .options(
            selectinload(Artwork.images),
            selectinload(Artwork.tags),
            selectinload(Artwork.sources),
        )
        .where(Artwork.author_ref_id == author_id)
        .order_by(Artwork.created_at.desc())
    )

    count_q = select(func.count()).select_from(
        select(Artwork.id).where(Artwork.author_ref_id == author_id).subquery()
    )
    total: int = (await db.execute(count_q)).scalar_one()

    q = q.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(q)).scalars().all()
    return list(rows), total
