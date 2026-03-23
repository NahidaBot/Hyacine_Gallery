"""tag_service 单元测试。"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.artwork import ArtworkCreate
from app.schemas.tag import TagCreate, TagTypeCreate, TagTypeUpdate, TagUpdate
from app.services.tag_service import (
    create_tag,
    create_tag_type,
    delete_tag,
    delete_tag_type,
    get_tag_by_id,
    get_tag_by_name,
    get_tag_types,
    get_tags,
    merge_tags,
    seed_default_tag_types,
    update_tag,
    update_tag_type,
)

# ── Tag CRUD ──


async def test_create_tag(db: AsyncSession):
    tag = await create_tag(db, TagCreate(name="flower", type="general"))
    assert tag.id is not None
    assert tag.name == "flower"
    assert tag.type == "general"
    assert tag.alias_of_id is None


async def test_get_tag_by_name(db: AsyncSession):
    await create_tag(db, TagCreate(name="sunset"))
    found = await get_tag_by_name(db, "sunset")
    assert found is not None
    assert found.name == "sunset"


async def test_get_tag_by_name_not_found(db: AsyncSession):
    result = await get_tag_by_name(db, "nonexistent")
    assert result is None


async def test_get_tag_by_id(db: AsyncSession):
    tag = await create_tag(db, TagCreate(name="ocean"))
    found = await get_tag_by_id(db, tag.id)
    assert found is not None
    assert found.name == "ocean"


async def test_get_tag_by_id_not_found(db: AsyncSession):
    result = await get_tag_by_id(db, 99999)
    assert result is None


async def test_get_tags_with_counts(db: AsyncSession, sample_artwork):
    """sample_artwork 有 2 个标签 (landscape, sky)，它们应各有 count=1。"""
    results = await get_tags(db)
    tag_map = {tag.name: count for tag, count in results}
    assert tag_map["landscape"] == 1
    assert tag_map["sky"] == 1


async def test_get_tags_filter_type(db: AsyncSession):
    await create_tag(db, TagCreate(name="tagA", type="character"))
    await create_tag(db, TagCreate(name="tagB", type="general"))

    char_tags = await get_tags(db, type_filter="character")
    names = [t.name for t, _ in char_tags]
    assert "tagA" in names
    assert "tagB" not in names


async def test_update_tag(db: AsyncSession):
    tag = await create_tag(db, TagCreate(name="old_name", type="general"))
    updated = await update_tag(db, tag.id, TagUpdate(name="new_name", type="character"))
    assert updated is not None
    assert updated.name == "new_name"
    assert updated.type == "character"


async def test_update_tag_not_found(db: AsyncSession):
    result = await update_tag(db, 99999, TagUpdate(name="nope"))
    assert result is None


async def test_merge_tags(db: AsyncSession):
    from app.services.artwork_service import create_artwork

    tag_a = await create_tag(db, TagCreate(name="tag_keep"))
    tag_b = await create_tag(db, TagCreate(name="tag_merge"))

    artwork = await create_artwork(
        db,
        ArtworkCreate(
            platform="pixiv",
            pid="merge_test_1",
            tags=["tag_keep", "tag_merge"],
        ),
    )

    result = await merge_tags(db, tag_a.id, tag_b.id)
    assert result is not None
    assert result.id == tag_a.id

    # tag_merge 应设为 alias
    await db.refresh(tag_b)
    assert tag_b.alias_of_id == tag_a.id

    # artwork 的标签关联应迁移到 keep_tag
    await db.refresh(artwork, attribute_names=["tags"])
    tag_ids = {t.id for t in artwork.tags}
    assert tag_a.id in tag_ids


async def test_delete_tag(db: AsyncSession):
    tag = await create_tag(db, TagCreate(name="to_delete"))
    assert await delete_tag(db, tag.id) is True
    assert await get_tag_by_id(db, tag.id) is None


async def test_delete_tag_not_found(db: AsyncSession):
    assert await delete_tag(db, 99999) is False


# ── Tag Types ──


async def test_get_tag_types(db: AsyncSession):
    """conftest 已 seed 4 种默认类型。"""
    results = await get_tag_types(db)
    names = [tt.name for tt, _ in results]
    assert "general" in names
    assert "character" in names
    assert "artist" in names
    assert "meta" in names
    assert len(results) == 4


async def test_create_tag_type(db: AsyncSession):
    tt = await create_tag_type(
        db, TagTypeCreate(name="copyright", label="Copyright", color="blue", sort_order=5)
    )
    assert tt.id is not None
    assert tt.name == "copyright"
    assert tt.label == "Copyright"
    assert tt.color == "blue"
    assert tt.sort_order == 5


async def test_update_tag_type(db: AsyncSession):
    tt = await create_tag_type(db, TagTypeCreate(name="temp_type", label="Temp"))
    updated = await update_tag_type(db, tt.id, TagTypeUpdate(label="Updated Label", color="red"))
    assert updated is not None
    assert updated.label == "Updated Label"
    assert updated.color == "red"


async def test_update_tag_type_not_found(db: AsyncSession):
    result = await update_tag_type(db, 99999, TagTypeUpdate(label="nope"))
    assert result is None


async def test_delete_tag_type(db: AsyncSession):
    tt = await create_tag_type(db, TagTypeCreate(name="disposable"))
    assert await delete_tag_type(db, tt.id) is True


async def test_delete_tag_type_not_found(db: AsyncSession):
    assert await delete_tag_type(db, 99999) is False


async def test_seed_default_tag_types_idempotent(db: AsyncSession):
    """seed 已在 conftest 调用过一次，再调一次仍应只有 4 个类型。"""
    await seed_default_tag_types(db)
    results = await get_tag_types(db)
    assert len(results) == 4
