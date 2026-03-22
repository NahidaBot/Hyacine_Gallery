"""Bot 发布队列服务 — 管理 bot_post_queue 表的增删查改和状态流转。"""

from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bot import BotPostQueue


async def add_to_queue(
    db: AsyncSession,
    artwork_id: int,
    *,
    platform: str = "telegram",
    channel_id: str = "",
    priority: int = 100,
    added_by: str = "",
    added_by_user_id: int | None = None,
) -> BotPostQueue:
    """将作品加入发布队列。"""
    item = BotPostQueue(
        artwork_id=artwork_id,
        platform=platform,
        channel_id=channel_id,
        priority=priority,
        status="pending",
        added_by=added_by,
        added_by_user_id=added_by_user_id,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def list_queue(
    db: AsyncSession,
    *,
    status: str | None = "pending",
    platform: str = "telegram",
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[BotPostQueue], int]:
    """列出队列条目，按优先级升序、创建时间升序排列。"""
    query = select(BotPostQueue).where(BotPostQueue.platform == platform)
    if status is not None:
        query = query.where(BotPostQueue.status == status)

    total_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(total_query)).scalar_one()

    query = query.order_by(BotPostQueue.priority.asc(), BotPostQueue.created_at.asc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    return list(result.scalars().all()), total


async def get_queue_item(db: AsyncSession, item_id: int) -> BotPostQueue | None:
    return await db.get(BotPostQueue, item_id)


async def delete_queue_item(db: AsyncSession, item_id: int) -> bool:
    item = await db.get(BotPostQueue, item_id)
    if not item:
        return False
    await db.delete(item)
    await db.commit()
    return True


async def update_priority(db: AsyncSession, item_id: int, priority: int) -> BotPostQueue | None:
    item = await db.get(BotPostQueue, item_id)
    if not item:
        return None
    item.priority = priority
    await db.commit()
    await db.refresh(item)
    return item


async def pop_next_item(db: AsyncSession, platform: str = "telegram") -> BotPostQueue | None:
    """取出下一条 pending 条目并标记为 processing。bot 单进程轮询，无竞态风险。"""
    stmt = (
        select(BotPostQueue)
        .where(BotPostQueue.platform == platform, BotPostQueue.status == "pending")
        .order_by(BotPostQueue.priority.asc(), BotPostQueue.created_at.asc())
        .limit(1)
    )
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()
    if not item:
        return None

    item.status = "processing"
    await db.commit()
    await db.refresh(item)
    return item


async def mark_done(db: AsyncSession, item_id: int) -> None:
    await db.execute(
        update(BotPostQueue)
        .where(BotPostQueue.id == item_id)
        .values(status="done", processed_at=datetime.now(UTC))
    )
    await db.commit()


async def mark_failed(db: AsyncSession, item_id: int, error: str = "") -> None:
    await db.execute(
        update(BotPostQueue)
        .where(BotPostQueue.id == item_id)
        .values(status="failed", error=error, processed_at=datetime.now(UTC))
    )
    await db.commit()


async def get_today_post_count(db: AsyncSession, platform: str = "telegram") -> int:
    """统计今日（UTC）已完成发布的队列条目数。"""
    from app.models.artwork import BotPostLog

    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    stmt = select(func.count()).where(
        BotPostLog.bot_platform == platform,
        BotPostLog.posted_at >= today_start,
    )
    return (await db.execute(stmt)).scalar_one()
