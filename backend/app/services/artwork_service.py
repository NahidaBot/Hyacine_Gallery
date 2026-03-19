import json

import imagehash
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.artwork import Artwork, ArtworkImage, ArtworkSource, ArtworkTag, BotPostLog, Tag
from app.schemas.artwork import ArtworkCreate, ArtworkUpdate


def _artwork_query():  # type: ignore[no-untyped-def]
    return select(Artwork).options(
        selectinload(Artwork.images),
        selectinload(Artwork.tags),
        selectinload(Artwork.sources),
    )


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
    """Find artwork via artwork_sources table."""
    source = await get_source_by_pid(db, platform, pid)
    if source:
        return await get_artwork_by_id(db, source.artwork_id)
    return None


async def get_random_artwork(db: AsyncSession) -> Artwork | None:
    query = _artwork_query().order_by(func.random()).limit(1)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def _get_or_create_tags(db: AsyncSession, tag_names: list[str]) -> list[Tag]:
    """Resolve tag names to Tag objects, creating any that don't exist."""
    seen: set[str] = set()
    unique_names: list[str] = []
    for raw in tag_names:
        name = raw.strip()
        if name and name not in seen:
            seen.add(name)
            unique_names.append(name)

    if not unique_names:
        return []

    existing = (await db.execute(select(Tag).where(Tag.name.in_(unique_names)))).scalars().all()
    existing_map = {t.name: t for t in existing}

    tags: list[Tag] = []
    for name in unique_names:
        if name in existing_map:
            tags.append(existing_map[name])
        else:
            new_tag = Tag(name=name)
            db.add(new_tag)
            existing_map[name] = new_tag
            tags.append(new_tag)

    if any(t.id is None for t in tags):
        await db.flush()

    return tags


async def create_artwork(
    db: AsyncSession, data: ArtworkCreate, raw_info: dict | None = None
) -> Artwork:
    tags = await _get_or_create_tags(db, data.tags)
    images = [ArtworkImage(page_index=i, url_original=url) for i, url in enumerate(data.image_urls)]

    primary_source = ArtworkSource(
        platform=data.platform,
        pid=data.pid,
        source_url=data.source_url,
        is_primary=True,
        raw_info=json.dumps(raw_info or {}, ensure_ascii=False),
    )

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
        sources=[primary_source],
    )
    db.add(artwork)

    await db.commit()
    await db.refresh(artwork, attribute_names=["images", "tags", "sources", "created_at", "updated_at"])
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
    await db.refresh(artwork, attribute_names=["images", "tags", "sources", "created_at", "updated_at"])
    return artwork


async def delete_artwork(db: AsyncSession, artwork_id: int) -> bool:
    artwork = await get_artwork_by_id(db, artwork_id)
    if not artwork:
        return False
    await db.delete(artwork)
    await db.commit()
    return True


async def delete_artwork_image(db: AsyncSession, artwork_id: int, image_id: int) -> bool:
    """Delete a single image from an artwork and reindex remaining pages."""
    artwork = await get_artwork_by_id(db, artwork_id)
    if not artwork:
        return False

    target = next((img for img in artwork.images if img.id == image_id), None)
    if not target:
        return False

    await db.delete(target)
    await db.flush()

    remaining = sorted(
        [img for img in artwork.images if img.id != image_id],
        key=lambda img: img.page_index,
    )
    for i, img in enumerate(remaining):
        img.page_index = i

    artwork.page_count = len(remaining)
    await db.commit()
    return True


# ── Source management ────────────────────────────────────────────


async def get_source_by_pid(db: AsyncSession, platform: str, pid: str) -> ArtworkSource | None:
    query = select(ArtworkSource).where(
        ArtworkSource.platform == platform, ArtworkSource.pid == pid
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def add_source(
    db: AsyncSession,
    artwork_id: int,
    platform: str,
    pid: str,
    source_url: str,
    raw_info: str = "{}",
) -> ArtworkSource:
    """Add a non-primary source to an existing artwork."""
    source = ArtworkSource(
        artwork_id=artwork_id,
        platform=platform,
        pid=pid,
        source_url=source_url,
        is_primary=False,
        raw_info=raw_info,
    )
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return source


async def delete_source(db: AsyncSession, artwork_id: int, source_id: int) -> bool:
    """Delete a non-primary source."""
    result = await db.execute(
        select(ArtworkSource).where(
            ArtworkSource.id == source_id,
            ArtworkSource.artwork_id == artwork_id,
            ArtworkSource.is_primary == False,  # noqa: E712
        )
    )
    source = result.scalar_one_or_none()
    if not source:
        return False
    await db.delete(source)
    await db.commit()
    return True


async def merge_artworks(db: AsyncSession, target_id: int, source_id: int) -> Artwork | None:
    """Merge source artwork into target artwork.

    - Moves all sources from source → target
    - Merges tags (union)
    - Moves post_logs from source → target
    - Deletes source artwork
    - Returns updated target
    """
    target = await get_artwork_by_id(db, target_id)
    source = await get_artwork_by_id(db, source_id)
    if not target or not source:
        return None

    # Move sources
    await db.execute(
        update(ArtworkSource)
        .where(ArtworkSource.artwork_id == source_id)
        .values(artwork_id=target_id, is_primary=False)
    )

    # Merge tags (union)
    target_tag_names = {t.name for t in target.tags}
    new_tag_names = [t.name for t in source.tags if t.name not in target_tag_names]
    if new_tag_names:
        extra_tags = await _get_or_create_tags(db, new_tag_names)
        target.tags = list(target.tags) + extra_tags

    # Move post_logs
    await db.execute(
        update(BotPostLog)
        .where(BotPostLog.artwork_id == source_id)
        .values(artwork_id=target_id)
    )

    # Delete source artwork (images cascade)
    await db.delete(source)
    await db.commit()

    return await get_artwork_by_id(db, target_id)


# ── pHash similarity search ─────────────────────────────────────


def _hamming_distance(h1: str, h2: str) -> int:
    """Compute hamming distance between two hex hash strings."""
    i1 = int(h1, 16)
    i2 = int(h2, 16)
    return bin(i1 ^ i2).count("1")


async def find_similar_by_phash(
    db: AsyncSession, phash: str, threshold: int = 8
) -> list[tuple[ArtworkImage, int]]:
    """Find artwork images with similar pHash. Returns (image, distance) pairs."""
    if not phash:
        return []

    # Load all non-empty phashes and filter in Python
    # (SQLite doesn't support bitwise operations efficiently)
    result = await db.execute(
        select(ArtworkImage).where(ArtworkImage.phash != "")
    )
    candidates = result.scalars().all()

    matches: list[tuple[ArtworkImage, int]] = []
    for img in candidates:
        dist = _hamming_distance(phash, img.phash)
        if dist <= threshold:
            matches.append((img, dist))

    matches.sort(key=lambda x: x[1])
    return matches
