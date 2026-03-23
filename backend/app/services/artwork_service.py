import json

from sqlalchemy import Select, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.artwork import Artwork, ArtworkImage, ArtworkSource, BotPostLog, Tag
from app.schemas.artwork import ArtworkCreate, ArtworkUpdate
from app.services.author_service import get_or_create_author


def _artwork_query() -> Select[tuple[Artwork]]:
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
    author_id: int | None = None,
    author_name: str | None = None,
) -> tuple[list[Artwork], int]:
    query = _artwork_query()

    if platform:
        query = query.where(Artwork.platform == platform)
    if tag:
        query = query.where(Artwork.tags.any(Tag.name == tag))
    if author_id:
        query = query.where(Artwork.author_ref_id == author_id)
    if author_name:
        from app.models.author import Author

        name_pattern = f"%{author_name}%"
        author_subq = select(Author.id).where(
            func.lower(Author.name).like(func.lower(name_pattern))
        )
        query = query.where(
            Artwork.author_ref_id.in_(author_subq)
            | func.lower(Artwork.author).like(func.lower(name_pattern))
        )
    if q:
        # 优先尝试 FTS 全文搜索，无结果时 fallback 到 LIKE
        from app.services.fts_service import fts_search_artwork_ids

        fts_ids = await fts_search_artwork_ids(db, q)
        if fts_ids:
            query = query.where(Artwork.id.in_(fts_ids))
        else:
            pattern = f"%{q}%"
            query = query.where(
                func.lower(Artwork.title).like(func.lower(pattern))
                | func.lower(Artwork.title_zh).like(func.lower(pattern))
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
    """通过 artwork_sources 表查找作品。"""
    source = await get_source_by_pid(db, platform, pid)
    if source:
        return await get_artwork_by_id(db, source.artwork_id)
    return None


async def get_random_artwork(db: AsyncSession) -> Artwork | None:
    query = _artwork_query().order_by(func.random()).limit(1)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def _get_or_create_tags(db: AsyncSession, tag_names: list[str]) -> list[Tag]:
    """将标签名称解析为 Tag 对象，不存在的自动创建。"""
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
    db: AsyncSession, data: ArtworkCreate, raw_info: dict[str, object] | None = None
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

    # 关联或创建作者记录
    author_ref = None
    if data.author and data.author_id:
        author_ref = await get_or_create_author(
            db, platform=data.platform, platform_uid=data.author_id, name=data.author
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
        author_ref=author_ref,
    )
    db.add(artwork)

    await db.commit()
    await db.refresh(
        artwork, attribute_names=["images", "tags", "sources", "created_at", "updated_at"]
    )
    return artwork


async def update_artwork(db: AsyncSession, artwork_id: int, data: ArtworkUpdate) -> Artwork | None:
    artwork = await get_artwork_by_id(db, artwork_id)
    if not artwork:
        return None

    for field in ("title", "title_zh", "author", "author_id", "source_url", "is_nsfw", "is_ai"):
        value = getattr(data, field)
        if value is not None:
            setattr(artwork, field, value)

    # 作者信息变更时同步更新 author_ref
    new_author = data.author if data.author is not None else artwork.author
    new_author_id = data.author_id if data.author_id is not None else artwork.author_id
    if (data.author is not None or data.author_id is not None) and new_author and new_author_id:
        author_ref = await get_or_create_author(
            db, platform=artwork.platform, platform_uid=new_author_id, name=new_author
        )
        artwork.author_ref = author_ref

    if data.tags is not None:
        artwork.tags = await _get_or_create_tags(db, data.tags)

    await db.commit()
    await db.refresh(
        artwork, attribute_names=["images", "tags", "sources", "created_at", "updated_at"]
    )
    return artwork


async def delete_artwork(db: AsyncSession, artwork_id: int) -> bool:
    artwork = await get_artwork_by_id(db, artwork_id)
    if not artwork:
        return False
    await db.delete(artwork)
    await db.commit()
    return True


async def delete_artwork_image(db: AsyncSession, artwork_id: int, image_id: int) -> bool:
    """从作品中删除单张图片并重新排序剩余页面。"""
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


# ── 来源管理 ────────────────────────────────────────────────────


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
    """为已有作品添加非主要来源。"""
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
    """删除非主要来源。"""
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
    """将源作品合并到目标作品。

    - 将所有来源从源作品迁移到目标作品
    - 合并标签（取并集）
    - 将发布日志从源作品迁移到目标作品
    - 删除源作品
    - 返回更新后的目标作品
    """
    target = await get_artwork_by_id(db, target_id)
    source = await get_artwork_by_id(db, source_id)
    if not target or not source:
        return None

    # 迁移来源
    await db.execute(
        update(ArtworkSource)
        .where(ArtworkSource.artwork_id == source_id)
        .values(artwork_id=target_id, is_primary=False)
    )

    # 合并标签（取并集）
    target_tag_names = {t.name for t in target.tags}
    new_tag_names = [t.name for t in source.tags if t.name not in target_tag_names]
    if new_tag_names:
        extra_tags = await _get_or_create_tags(db, new_tag_names)
        target.tags = list(target.tags) + extra_tags

    # 迁移发布日志
    await db.execute(
        update(BotPostLog).where(BotPostLog.artwork_id == source_id).values(artwork_id=target_id)
    )

    # 刷新 SQL UPDATE，然后使 ORM 缓存失效，避免 delete-orphan
    # 级联删除已迁移到目标作品的来源和发布日志
    await db.flush()
    db.expire(source)

    # 删除源作品（图片级联删除，来源和发布日志已迁移）
    await db.delete(source)
    await db.commit()

    return await get_artwork_by_id(db, target_id)


# ── pHash 相似度搜索 ────────────────────────────────────────────


def _hamming_distance(h1: str, h2: str) -> int:
    """计算两个十六进制哈希字符串之间的汉明距离。"""
    i1 = int(h1, 16)
    i2 = int(h2, 16)
    return bin(i1 ^ i2).count("1")


async def find_similar_by_phash(
    db: AsyncSession, phash: str, threshold: int = 8
) -> list[tuple[ArtworkImage, int]]:
    """查找具有相似 pHash 的作品图片。返回 (image, distance) 对。"""
    if not phash:
        return []

    # 加载所有非空 pHash 并在 Python 中过滤
    # （SQLite 不能高效支持位运算）
    result = await db.execute(select(ArtworkImage).where(ArtworkImage.phash != ""))
    candidates = result.scalars().all()

    matches: list[tuple[ArtworkImage, int]] = []
    for img in candidates:
        dist = _hamming_distance(phash, img.phash)
        if dist <= threshold:
            matches.append((img, dist))

    matches.sort(key=lambda x: x[1])
    return matches


async def backfill_author_refs(db: AsyncSession) -> int:
    """为所有缺少 author_ref_id 但有 author/author_id 的作品回填作者关联。返回更新的数量。"""
    result = await db.execute(
        select(Artwork).where(
            Artwork.author_ref_id.is_(None),
            Artwork.author != "",
            Artwork.author_id != "",
        )
    )
    artworks = result.scalars().all()
    count = 0
    for aw in artworks:
        author_ref = await get_or_create_author(
            db, platform=aw.platform, platform_uid=aw.author_id, name=aw.author
        )
        aw.author_ref = author_ref
        count += 1
    await db.commit()
    return count
