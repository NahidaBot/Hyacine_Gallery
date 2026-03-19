from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.artwork import ArtworkTag, Tag, TagType
from app.schemas.tag import TagCreate, TagTypeCreate, TagTypeUpdate, TagUpdate


async def get_tags(
    db: AsyncSession,
    *,
    type_filter: str | None = None,
) -> list[tuple[Tag, int]]:
    """Return all tags with their artwork counts."""
    count_sub = (
        select(ArtworkTag.tag_id, func.count().label("cnt"))
        .group_by(ArtworkTag.tag_id)
        .subquery()
    )

    query = select(Tag, func.coalesce(count_sub.c.cnt, 0)).outerjoin(
        count_sub, Tag.id == count_sub.c.tag_id
    )

    if type_filter:
        query = query.where(Tag.type == type_filter)

    query = query.order_by(func.coalesce(count_sub.c.cnt, 0).desc())
    result = await db.execute(query)
    return [(tag, count) for tag, count in result.all()]


async def get_tag_by_name(db: AsyncSession, name: str) -> Tag | None:
    result = await db.execute(select(Tag).where(Tag.name == name))
    return result.scalar_one_or_none()


async def get_tag_by_id(db: AsyncSession, tag_id: int) -> Tag | None:
    result = await db.execute(select(Tag).where(Tag.id == tag_id))
    return result.scalar_one_or_none()


async def create_tag(db: AsyncSession, data: TagCreate) -> Tag:
    tag = Tag(name=data.name, type=data.type, alias_of_id=data.alias_of_id)
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    return tag


async def update_tag(db: AsyncSession, tag_id: int, data: TagUpdate) -> Tag | None:
    tag = await get_tag_by_id(db, tag_id)
    if not tag:
        return None

    for field in ("name", "type", "alias_of_id"):
        value = getattr(data, field)
        if value is not None:
            setattr(tag, field, value)

    await db.commit()
    await db.refresh(tag)
    return tag


async def delete_tag(db: AsyncSession, tag_id: int) -> bool:
    tag = await get_tag_by_id(db, tag_id)
    if not tag:
        return False
    await db.delete(tag)
    await db.commit()
    return True


# ── Tag Types ──


async def get_tag_types(db: AsyncSession) -> list[tuple[TagType, int]]:
    """Return all tag types with their tag counts, ordered by sort_order."""
    count_sub = (
        select(Tag.type, func.count().label("cnt"))
        .group_by(Tag.type)
        .subquery()
    )
    query = (
        select(TagType, func.coalesce(count_sub.c.cnt, 0))
        .outerjoin(count_sub, TagType.name == count_sub.c.type)
        .order_by(TagType.sort_order, TagType.name)
    )
    result = await db.execute(query)
    return [(tt, count) for tt, count in result.all()]


async def get_tag_type_by_id(db: AsyncSession, tt_id: int) -> TagType | None:
    result = await db.execute(select(TagType).where(TagType.id == tt_id))
    return result.scalar_one_or_none()


async def create_tag_type(db: AsyncSession, data: TagTypeCreate) -> TagType:
    tt = TagType(name=data.name, label=data.label, color=data.color, sort_order=data.sort_order)
    db.add(tt)
    await db.commit()
    await db.refresh(tt)
    return tt


async def update_tag_type(db: AsyncSession, tt_id: int, data: TagTypeUpdate) -> TagType | None:
    tt = await get_tag_type_by_id(db, tt_id)
    if not tt:
        return None
    for field in ("name", "label", "color", "sort_order"):
        value = getattr(data, field)
        if value is not None:
            setattr(tt, field, value)
    await db.commit()
    await db.refresh(tt)
    return tt


async def delete_tag_type(db: AsyncSession, tt_id: int) -> bool:
    tt = await get_tag_type_by_id(db, tt_id)
    if not tt:
        return False
    await db.delete(tt)
    await db.commit()
    return True


async def seed_default_tag_types(db: AsyncSession) -> None:
    """Insert default tag types if the table is empty."""
    result = await db.execute(select(func.count()).select_from(TagType))
    if result.scalar_one() > 0:
        return

    defaults = [
        TagType(name="general", label="General", color="neutral", sort_order=0),
        TagType(name="character", label="Character", color="green", sort_order=1),
        TagType(name="artist", label="Artist", color="orange", sort_order=2),
        TagType(name="meta", label="Meta", color="purple", sort_order=3),
    ]
    db.add_all(defaults)
    await db.commit()
