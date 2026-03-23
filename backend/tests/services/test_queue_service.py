"""queue_service 单元测试。"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.queue_service import (
    add_to_queue,
    delete_queue_item,
    get_queue_item,
    get_today_post_count,
    list_queue,
    mark_done,
    mark_failed,
    pop_next_item,
    update_priority,
)

# ── 添加 ──────────────────────────────────────────────────────────


async def test_add_to_queue(db: AsyncSession, sample_artwork):
    item = await add_to_queue(
        db,
        sample_artwork.id,
        platform="telegram",
        channel_id="-100123",
        priority=50,
        added_by="tester",
    )
    assert item.id is not None
    assert item.artwork_id == sample_artwork.id
    assert item.platform == "telegram"
    assert item.channel_id == "-100123"
    assert item.priority == 50
    assert item.status == "pending"
    assert item.added_by == "tester"


# ── 列表 ──────────────────────────────────────────────────────────


async def test_list_queue_pending(db: AsyncSession, sample_artwork):
    await add_to_queue(db, sample_artwork.id, priority=10)
    await add_to_queue(db, sample_artwork.id, priority=20)

    items, total = await list_queue(db, status="pending")
    assert total == 2
    assert len(items) == 2


async def test_list_queue_all(db: AsyncSession, sample_artwork):
    await add_to_queue(db, sample_artwork.id)
    # 将一个标记为 done
    popped = await pop_next_item(db)
    assert popped is not None
    await mark_done(db, popped.id)

    # 再添加一个 pending
    await add_to_queue(db, sample_artwork.id, priority=200)

    items, total = await list_queue(db, status=None)
    assert total == 2


async def test_list_queue_ordered(db: AsyncSession, sample_artwork):
    await add_to_queue(db, sample_artwork.id, priority=100)
    await add_to_queue(db, sample_artwork.id, priority=10)
    await add_to_queue(db, sample_artwork.id, priority=50)

    items, total = await list_queue(db, status="pending")
    assert total == 3
    priorities = [it.priority for it in items]
    assert priorities == [10, 50, 100]


# ── 单条查询与删除 ────────────────────────────────────────────────


async def test_get_queue_item(db: AsyncSession, sample_artwork):
    item = await add_to_queue(db, sample_artwork.id)
    found = await get_queue_item(db, item.id)
    assert found is not None
    assert found.id == item.id


async def test_get_queue_item_not_found(db: AsyncSession):
    assert await get_queue_item(db, 999999) is None


async def test_delete_queue_item(db: AsyncSession, sample_artwork):
    item = await add_to_queue(db, sample_artwork.id)
    assert await delete_queue_item(db, item.id) is True
    assert await get_queue_item(db, item.id) is None


async def test_delete_queue_item_not_found(db: AsyncSession):
    assert await delete_queue_item(db, 999999) is False


# ── 优先级更新 ────────────────────────────────────────────────────


async def test_update_priority(db: AsyncSession, sample_artwork):
    item = await add_to_queue(db, sample_artwork.id, priority=100)
    updated = await update_priority(db, item.id, 5)
    assert updated is not None
    assert updated.priority == 5


async def test_update_priority_not_found(db: AsyncSession):
    assert await update_priority(db, 999999, 1) is None


# ── Pop ───────────────────────────────────────────────────────────


async def test_pop_next_item(db: AsyncSession, sample_artwork):
    await add_to_queue(db, sample_artwork.id, priority=100)
    await add_to_queue(db, sample_artwork.id, priority=10)

    popped = await pop_next_item(db)
    assert popped is not None
    assert popped.priority == 10


async def test_pop_next_item_marks_processing(db: AsyncSession, sample_artwork):
    await add_to_queue(db, sample_artwork.id)
    popped = await pop_next_item(db)
    assert popped is not None
    assert popped.status == "processing"


async def test_pop_next_item_empty(db: AsyncSession):
    result = await pop_next_item(db)
    assert result is None


# ── 状态流转 ──────────────────────────────────────────────────────


async def test_mark_done(db: AsyncSession, sample_artwork):
    await add_to_queue(db, sample_artwork.id)
    popped = await pop_next_item(db)
    assert popped is not None

    await mark_done(db, popped.id)
    item = await get_queue_item(db, popped.id)
    assert item is not None
    assert item.status == "done"
    assert item.processed_at is not None


async def test_mark_failed(db: AsyncSession, sample_artwork):
    await add_to_queue(db, sample_artwork.id)
    popped = await pop_next_item(db)
    assert popped is not None

    await mark_failed(db, popped.id, error="timeout")
    item = await get_queue_item(db, popped.id)
    assert item is not None
    assert item.status == "failed"
    assert item.error == "timeout"
    assert item.processed_at is not None


# ── 今日发布计数 ──────────────────────────────────────────────────


async def test_get_today_post_count(db: AsyncSession, sample_post_log):
    count = await get_today_post_count(db, platform="telegram")
    assert count == 1
