from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.artwork import Artwork, ArtworkTag
from app.schemas.artwork import ArtworkCreate


async def get_artworks(
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 20,
    platform: str | None = None,
    tag: str | None = None,
    q: str | None = None,
) -> tuple[list[Artwork], int]:
    query = select(Artwork).options(selectinload(Artwork.tags))

    if platform:
        query = query.where(Artwork.platform == platform)
    if tag:
        query = query.join(ArtworkTag).where(ArtworkTag.tag == tag)
    if q:
        query = query.where(Artwork.title.ilike(f"%{q}%") | Artwork.author.ilike(f"%{q}%"))

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # Paginate
    query = query.order_by(Artwork.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    artworks = list(result.scalars().all())

    return artworks, total


async def get_artwork_by_id(db: AsyncSession, artwork_id: int) -> Artwork | None:
    query = select(Artwork).options(selectinload(Artwork.tags)).where(Artwork.id == artwork_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_artwork_by_pid(db: AsyncSession, platform: str, pid: str) -> Artwork | None:
    query = (
        select(Artwork)
        .options(selectinload(Artwork.tags))
        .where(Artwork.platform == platform, Artwork.pid == pid)
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_random_artwork(db: AsyncSession) -> Artwork | None:
    query = select(Artwork).options(selectinload(Artwork.tags)).order_by(func.random()).limit(1)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def create_artwork(db: AsyncSession, data: ArtworkCreate) -> Artwork:
    artwork = Artwork(
        platform=data.platform,
        pid=data.pid,
        title=data.title,
        author=data.author,
        author_id=data.author_id,
        source_url=data.source_url,
        page_count=data.page_count,
        width=data.width,
        height=data.height,
        is_nsfw=data.is_nsfw,
        is_ai=data.is_ai,
    )
    for tag_name in data.tags:
        artwork.tags.append(ArtworkTag(tag=tag_name))

    db.add(artwork)
    await db.commit()
    await db.refresh(artwork)
    return artwork


async def delete_artwork(db: AsyncSession, artwork_id: int) -> bool:
    artwork = await get_artwork_by_id(db, artwork_id)
    if not artwork:
        return False
    await db.delete(artwork)
    await db.commit()
    return True


async def get_tags_with_count(db: AsyncSession) -> list[tuple[str, int]]:
    query = (
        select(ArtworkTag.tag, func.count(ArtworkTag.id))
        .group_by(ArtworkTag.tag)
        .order_by(func.count(ArtworkTag.id).desc())
    )
    result = await db.execute(query)
    return list(result.all())
