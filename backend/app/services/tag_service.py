from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.artwork import ArtworkTag, Tag
from app.schemas.tag import TagCreate, TagUpdate


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
