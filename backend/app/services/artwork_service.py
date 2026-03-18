from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.artwork import Artwork, ArtworkImage, ArtworkTag, Tag
from app.schemas.artwork import ArtworkCreate, ArtworkUpdate


def _artwork_query():  # type: ignore[no-untyped-def]
    return select(Artwork).options(selectinload(Artwork.images), selectinload(Artwork.tags))


async def get_artworks(
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 20,
    platform: str | None = None,
    tag: str | None = None,
    q: str | None = None,
) -> tuple[list[Artwork], int]:
    query = _artwork_query()

    if platform:
        query = query.where(Artwork.platform == platform)
    if tag:
        query = query.where(Artwork.tags.any(Tag.name == tag))
    if q:
        pattern = f"%{q}%"
        query = query.where(
            func.lower(Artwork.title).like(func.lower(pattern))
            | func.lower(Artwork.author).like(func.lower(pattern))
        )

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    query = query.order_by(Artwork.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)

    return list(result.scalars().unique().all()), total


async def get_artwork_by_id(db: AsyncSession, artwork_id: int) -> Artwork | None:
    query = _artwork_query().where(Artwork.id == artwork_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_artwork_by_pid(db: AsyncSession, platform: str, pid: str) -> Artwork | None:
    query = _artwork_query().where(Artwork.platform == platform, Artwork.pid == pid)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_random_artwork(db: AsyncSession) -> Artwork | None:
    query = _artwork_query().order_by(func.random()).limit(1)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def _get_or_create_tags(db: AsyncSession, tag_names: list[str]) -> list[Tag]:
    """Resolve tag names to Tag objects, creating any that don't exist."""
    if not tag_names:
        return []

    existing = (await db.execute(select(Tag).where(Tag.name.in_(tag_names)))).scalars().all()
    existing_map = {t.name: t for t in existing}

    tags: list[Tag] = []
    for name in tag_names:
        if name in existing_map:
            tags.append(existing_map[name])
        else:
            new_tag = Tag(name=name)
            db.add(new_tag)
            tags.append(new_tag)

    if any(t.id is None for t in tags):
        await db.flush()

    return tags


async def create_artwork(db: AsyncSession, data: ArtworkCreate) -> Artwork:
    # Resolve tags before adding artwork to session to avoid lazy-load in async context
    tags = await _get_or_create_tags(db, data.tags)
    images = [ArtworkImage(page_index=i, url_original=url) for i, url in enumerate(data.image_urls)]

    artwork = Artwork(
        platform=data.platform,
        pid=data.pid,
        title=data.title,
        author=data.author,
        author_id=data.author_id,
        source_url=data.source_url,
        page_count=data.page_count,
        is_nsfw=data.is_nsfw,
        is_ai=data.is_ai,
        images=images,
        tags=tags,
    )
    db.add(artwork)

    await db.commit()
    await db.refresh(artwork, attribute_names=["images", "tags", "created_at", "updated_at"])
    return artwork


async def update_artwork(db: AsyncSession, artwork_id: int, data: ArtworkUpdate) -> Artwork | None:
    artwork = await get_artwork_by_id(db, artwork_id)
    if not artwork:
        return None

    for field in ("title", "author", "author_id", "source_url", "is_nsfw", "is_ai"):
        value = getattr(data, field)
        if value is not None:
            setattr(artwork, field, value)

    if data.tags is not None:
        artwork.tags = await _get_or_create_tags(db, data.tags)

    await db.commit()
    await db.refresh(artwork, attribute_names=["images", "tags", "created_at", "updated_at"])
    return artwork


async def delete_artwork(db: AsyncSession, artwork_id: int) -> bool:
    artwork = await get_artwork_by_id(db, artwork_id)
    if not artwork:
        return False
    await db.delete(artwork)
    await db.commit()
    return True
