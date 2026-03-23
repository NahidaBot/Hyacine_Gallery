"""author_service 单元测试。"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.artwork import ArtworkCreate
from app.schemas.author import AuthorCreate, AuthorUpdate
from app.services.author_service import (
    create_author,
    delete_author,
    get_artworks_by_author,
    get_artworks_by_author_with_canonical,
    get_author,
    get_author_by_name,
    get_author_by_platform_uid,
    get_or_create_author,
    list_authors,
    update_author,
)

# ── CRUD ──


async def test_create_author(db: AsyncSession):
    author = await create_author(
        db, AuthorCreate(name="Alice", platform="pixiv", platform_uid="alice_001")
    )
    assert author.id is not None
    assert author.name == "Alice"
    assert author.platform == "pixiv"
    assert author.platform_uid == "alice_001"


async def test_get_author(db: AsyncSession):
    author = await create_author(
        db, AuthorCreate(name="Bob", platform="twitter", platform_uid="bob_tw")
    )
    found = await get_author(db, author.id)
    assert found is not None
    assert found.name == "Bob"


async def test_get_author_not_found(db: AsyncSession):
    assert await get_author(db, 99999) is None


async def test_get_author_by_platform_uid(db: AsyncSession):
    await create_author(db, AuthorCreate(name="Carol", platform="pixiv", platform_uid="carol_px"))
    found = await get_author_by_platform_uid(db, "pixiv", "carol_px")
    assert found is not None
    assert found.name == "Carol"


async def test_get_author_by_platform_uid_not_found(db: AsyncSession):
    result = await get_author_by_platform_uid(db, "pixiv", "nonexistent")
    assert result is None


async def test_get_or_create_author_new(db: AsyncSession):
    author = await get_or_create_author(db, "pixiv", "new_uid", "NewArtist")
    assert author.id is not None
    assert author.name == "NewArtist"
    assert author.platform_uid == "new_uid"


async def test_get_or_create_author_existing(db: AsyncSession):
    original = await create_author(
        db, AuthorCreate(name="Existing", platform="pixiv", platform_uid="exist_001")
    )
    returned = await get_or_create_author(db, "pixiv", "exist_001", "Existing")
    assert returned.id == original.id


async def test_list_authors_paginated(db: AsyncSession):
    for i in range(3):
        await create_author(
            db,
            AuthorCreate(name=f"Author_{i}", platform="pixiv", platform_uid=f"uid_{i}"),
        )

    authors, total = await list_authors(db, page=1, page_size=2)
    assert total == 3
    assert len(authors) == 2

    authors_p2, total_p2 = await list_authors(db, page=2, page_size=2)
    assert total_p2 == 3
    assert len(authors_p2) == 1


async def test_list_authors_filter_platform(db: AsyncSession):
    await create_author(db, AuthorCreate(name="PxArtist", platform="pixiv", platform_uid="px_1"))
    await create_author(db, AuthorCreate(name="TwArtist", platform="twitter", platform_uid="tw_1"))

    pixiv_list, total = await list_authors(db, platform="pixiv")
    assert total == 1
    assert pixiv_list[0].name == "PxArtist"


async def test_update_author(db: AsyncSession):
    author = await create_author(
        db, AuthorCreate(name="OldName", platform="pixiv", platform_uid="upd_001")
    )
    updated = await update_author(db, author.id, AuthorUpdate(name="NewName"))
    assert updated is not None
    assert updated.name == "NewName"


async def test_update_author_not_found(db: AsyncSession):
    result = await update_author(db, 99999, AuthorUpdate(name="nope"))
    assert result is None


async def test_delete_author(db: AsyncSession):
    author = await create_author(
        db, AuthorCreate(name="ToDelete", platform="pixiv", platform_uid="del_001")
    )
    assert await delete_author(db, author.id) is True
    assert await get_author(db, author.id) is None


async def test_delete_author_not_found(db: AsyncSession):
    assert await delete_author(db, 99999) is False


async def test_get_author_by_name(db: AsyncSession):
    await create_author(db, AuthorCreate(name="FindMe", platform="pixiv", platform_uid="find_001"))
    found = await get_author_by_name(db, "FindMe")
    assert found is not None
    assert found.name == "FindMe"


async def test_get_author_by_name_not_found(db: AsyncSession):
    assert await get_author_by_name(db, "ghost") is None


# ── Artwork 关联查询 ──


async def test_get_artworks_by_author(db: AsyncSession):
    from app.services.artwork_service import create_artwork

    author = await create_author(
        db, AuthorCreate(name="ArtAuthor", platform="pixiv", platform_uid="art_001")
    )
    artwork = await create_artwork(
        db,
        ArtworkCreate(
            platform="pixiv",
            pid="aw_author_test",
            title="Author Test",
            tags=[],
        ),
    )
    artwork.author_ref_id = author.id
    await db.commit()

    artworks, total = await get_artworks_by_author(db, author.id)
    assert total == 1
    assert artworks[0].id == artwork.id


async def test_get_artworks_by_author_with_canonical(db: AsyncSession):
    from app.services.artwork_service import create_artwork

    # 规范作者 A
    author_a = await create_author(
        db, AuthorCreate(name="CanonAuthor", platform="pixiv", platform_uid="canon_001")
    )
    # 别名作者 B，指向 A
    author_b = await create_author(
        db,
        AuthorCreate(
            name="AliasAuthor",
            platform="twitter",
            platform_uid="alias_001",
            canonical_id=author_a.id,
        ),
    )

    aw1 = await create_artwork(
        db,
        ArtworkCreate(platform="pixiv", pid="canon_aw1", tags=[]),
    )
    aw1.author_ref_id = author_a.id

    aw2 = await create_artwork(
        db,
        ArtworkCreate(platform="twitter", pid="alias_aw2", tags=[]),
    )
    aw2.author_ref_id = author_b.id
    await db.commit()

    # 从 canonical 作者查询，应返回两个作品
    artworks, total = await get_artworks_by_author_with_canonical(db, author_a.id)
    assert total == 2
    ids = {aw.id for aw in artworks}
    assert aw1.id in ids
    assert aw2.id in ids

    # 从 alias 作者查询，也应返回两个作品
    artworks2, total2 = await get_artworks_by_author_with_canonical(db, author_b.id)
    assert total2 == 2
