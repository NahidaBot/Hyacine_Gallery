"""tag_dedup_service 单元测试。"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.tag import TagCreate
from app.services.tag_dedup_service import find_duplicate_tags
from app.services.tag_service import create_tag


async def test_find_duplicates_match(db: AsyncSession):
    """相似度高于阈值的标签对应被检出。"""
    await create_tag(db, TagCreate(name="original", type="general"))
    await create_tag(db, TagCreate(name="orignal", type="general"))
    results = await find_duplicate_tags(db, threshold=0.8)
    assert len(results) >= 1
    pair = results[0]
    names = {pair["tag_a"]["name"], pair["tag_b"]["name"]}
    assert names == {"original", "orignal"}
    assert pair["similarity"] >= 0.8


async def test_find_duplicates_no_match(db: AsyncSession):
    """差异大的标签不应被检出。"""
    await create_tag(db, TagCreate(name="cat", type="general"))
    await create_tag(db, TagCreate(name="mountain", type="general"))
    results = await find_duplicate_tags(db, threshold=0.8)
    assert results == []


async def test_find_duplicates_excludes_aliases(db: AsyncSession):
    """已设置 alias_of_id 的标签应被排除。"""
    tag_a = await create_tag(db, TagCreate(name="original", type="general"))
    await create_tag(db, TagCreate(name="orignal", type="general", alias_of_id=tag_a.id))
    results = await find_duplicate_tags(db, threshold=0.8)
    # tag_b 有 alias_of_id，应被排除，不会与 tag_a 配对
    assert results == []


async def test_find_duplicates_empty(db: AsyncSession):
    """没有用户创建的标签时应返回空列表。"""
    results = await find_duplicate_tags(db, threshold=0.8)
    assert results == []
