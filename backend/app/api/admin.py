import json

from fastapi import APIRouter, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import AdminDep, DBDep
from app.crawlers import crawl
from app.schemas.artwork import (
    ArtworkAddSourceRequest,
    ArtworkCreate,
    ArtworkImportRequest,
    ArtworkMergeRequest,
    ArtworkResponse,
    ArtworkSourceResponse,
    ArtworkUpdate,
    ImportResponse,
    SimilarArtworkInfo,
)
from app.schemas.tag import TagCreate, TagResponse, TagTypeCreate, TagTypeResponse, TagTypeUpdate, TagUpdate
from app.services import artwork_service, storage_service, tag_service

router = APIRouter(dependencies=[AdminDep])


# --- Artworks ---


@router.post("/artworks", response_model=ArtworkResponse)
async def create_artwork(data: ArtworkCreate, db: AsyncSession = DBDep) -> ArtworkResponse:
    artwork = await artwork_service.create_artwork(db, data)
    return ArtworkResponse.model_validate(artwork)


@router.put("/artworks/{artwork_id}", response_model=ArtworkResponse)
async def update_artwork(
    artwork_id: int, data: ArtworkUpdate, db: AsyncSession = DBDep
) -> ArtworkResponse:
    artwork = await artwork_service.update_artwork(db, artwork_id, data)
    if not artwork:
        raise HTTPException(404, "Artwork not found")
    return ArtworkResponse.model_validate(artwork)


@router.delete("/artworks/{artwork_id}")
async def delete_artwork(artwork_id: int, db: AsyncSession = DBDep) -> dict[str, str]:
    deleted = await artwork_service.delete_artwork(db, artwork_id)
    if not deleted:
        raise HTTPException(404, "Artwork not found")
    return {"status": "deleted"}


@router.delete("/artworks/{artwork_id}/images/{image_id}")
async def delete_artwork_image(
    artwork_id: int, image_id: int, db: AsyncSession = DBDep
) -> dict[str, str]:
    deleted = await artwork_service.delete_artwork_image(db, artwork_id, image_id)
    if not deleted:
        raise HTTPException(404, "Image not found")
    return {"status": "deleted"}


@router.post("/artworks/import", response_model=ImportResponse)
async def import_artwork(
    data: ArtworkImportRequest, db: AsyncSession = DBDep
) -> ImportResponse:
    """Crawl a URL, deduplicate via platform+pid and pHash, create or merge."""
    result = await crawl(data.url)
    if not result.success:
        raise HTTPException(422, f"Crawl failed: {result.error}")

    # Step 1: Same-platform dedup via artwork_sources
    existing = await artwork_service.get_artwork_by_pid(db, result.platform, result.pid)
    if existing:
        return ImportResponse(
            artwork=ArtworkResponse.model_validate(existing),
            message="Already exists (same platform+pid).",
        )

    # Step 2: Create artwork + download images (pHash computed during download)
    all_tags = list(dict.fromkeys(result.tags + data.tags))
    create_data = ArtworkCreate(
        platform=result.platform,
        pid=result.pid,
        title=result.title,
        author=result.author,
        author_id=result.author_id,
        source_url=result.source_url,
        page_count=len(result.image_urls) or 1,
        is_nsfw=result.is_nsfw,
        is_ai=result.is_ai,
        image_urls=result.image_urls,
        tags=all_tags,
    )
    artwork = await artwork_service.create_artwork(db, create_data, raw_info=result.raw_info)
    await storage_service.download_and_store_images(db, artwork)
    await db.refresh(artwork)
    await db.refresh(artwork, attribute_names=["images", "tags", "sources"])

    # Step 3: pHash cross-platform dedup
    first_image = next((img for img in artwork.images if img.phash), None)
    if first_image and first_image.phash:
        matches = await artwork_service.find_similar_by_phash(db, first_image.phash)
        # Filter out matches from the artwork we just created
        matches = [(img, dist) for img, dist in matches if img.artwork_id != artwork.id]

        if matches:
            # Group by artwork_id, pick closest match per artwork
            seen_artwork_ids: set[int] = set()
            similar: list[SimilarArtworkInfo] = []
            for img, dist in matches:
                if img.artwork_id in seen_artwork_ids:
                    continue
                seen_artwork_ids.add(img.artwork_id)
                match_artwork = await artwork_service.get_artwork_by_id(db, img.artwork_id)
                if match_artwork:
                    thumb = match_artwork.images[0].url_thumb if match_artwork.images else ""
                    similar.append(SimilarArtworkInfo(
                        artwork_id=match_artwork.id,
                        distance=dist,
                        platform=match_artwork.platform,
                        pid=match_artwork.pid,
                        title=match_artwork.title,
                        thumb_url=thumb,
                    ))

            if similar and data.auto_merge:
                # Auto-merge: keep the one with more pages
                target = similar[0]
                target_artwork = await artwork_service.get_artwork_by_id(db, target.artwork_id)
                if target_artwork:
                    if artwork.page_count <= target_artwork.page_count:
                        # Merge new into existing (existing has more pages)
                        merged = await artwork_service.merge_artworks(
                            db, target.artwork_id, artwork.id
                        )
                        if merged:
                            return ImportResponse(
                                artwork=ArtworkResponse.model_validate(merged),
                                merged=True,
                                message=f"Auto-merged into artwork #{target.artwork_id} (pHash match, distance={target.distance}).",
                            )
                    else:
                        # Merge existing into new (new has more pages)
                        merged = await artwork_service.merge_artworks(
                            db, artwork.id, target.artwork_id
                        )
                        if merged:
                            return ImportResponse(
                                artwork=ArtworkResponse.model_validate(merged),
                                merged=True,
                                message=f"Auto-merged artwork #{target.artwork_id} into new #{artwork.id} (more pages).",
                            )

            if similar and not data.auto_merge:
                return ImportResponse(
                    artwork=ArtworkResponse.model_validate(artwork),
                    similar=similar,
                    message="Similar artworks found. Set auto_merge=true to merge automatically.",
                )

    return ImportResponse(
        artwork=ArtworkResponse.model_validate(artwork),
        message="Created new artwork.",
    )


# --- Artwork Sources ---


@router.post("/artworks/{artwork_id}/sources", response_model=ArtworkSourceResponse)
async def add_artwork_source(
    artwork_id: int, data: ArtworkAddSourceRequest, db: AsyncSession = DBDep
) -> ArtworkSourceResponse:
    """Crawl a URL and add it as a source to an existing artwork."""
    artwork = await artwork_service.get_artwork_by_id(db, artwork_id)
    if not artwork:
        raise HTTPException(404, "Artwork not found")

    result = await crawl(data.url)
    if not result.success:
        raise HTTPException(422, f"Crawl failed: {result.error}")

    # Check if this source already exists
    existing = await artwork_service.get_source_by_pid(db, result.platform, result.pid)
    if existing:
        raise HTTPException(409, f"Source {result.platform}/{result.pid} already linked to artwork #{existing.artwork_id}")

    source = await artwork_service.add_source(
        db, artwork_id, result.platform, result.pid, result.source_url,
        raw_info=json.dumps(result.raw_info or {}, ensure_ascii=False),
    )
    return ArtworkSourceResponse.model_validate(source)


@router.delete("/artworks/{artwork_id}/sources/{source_id}")
async def delete_artwork_source(
    artwork_id: int, source_id: int, db: AsyncSession = DBDep
) -> dict[str, str]:
    deleted = await artwork_service.delete_source(db, artwork_id, source_id)
    if not deleted:
        raise HTTPException(404, "Source not found or is primary")
    return {"status": "deleted"}


@router.post("/artworks/{artwork_id}/merge", response_model=ArtworkResponse)
async def merge_artwork(
    artwork_id: int, data: ArtworkMergeRequest, db: AsyncSession = DBDep
) -> ArtworkResponse:
    """Merge another artwork into this one."""
    if artwork_id == data.source_artwork_id:
        raise HTTPException(400, "Cannot merge artwork into itself")
    merged = await artwork_service.merge_artworks(db, artwork_id, data.source_artwork_id)
    if not merged:
        raise HTTPException(404, "Artwork not found")
    return ArtworkResponse.model_validate(merged)


# --- Tags ---


@router.post("/tags", response_model=TagResponse)
async def create_tag(data: TagCreate, db: AsyncSession = DBDep) -> TagResponse:
    tag = await tag_service.create_tag(db, data)
    return TagResponse(
        id=tag.id,
        name=tag.name,
        type=tag.type,
        alias_of_id=tag.alias_of_id,
        created_at=tag.created_at,
        artwork_count=0,
    )


@router.put("/tags/{tag_id}", response_model=TagResponse)
async def update_tag(tag_id: int, data: TagUpdate, db: AsyncSession = DBDep) -> TagResponse:
    tag = await tag_service.update_tag(db, tag_id, data)
    if not tag:
        raise HTTPException(404, "Tag not found")
    return TagResponse(
        id=tag.id,
        name=tag.name,
        type=tag.type,
        alias_of_id=tag.alias_of_id,
        created_at=tag.created_at,
        artwork_count=0,
    )


@router.delete("/tags/{tag_id}")
async def delete_tag(tag_id: int, db: AsyncSession = DBDep) -> dict[str, str]:
    deleted = await tag_service.delete_tag(db, tag_id)
    if not deleted:
        raise HTTPException(404, "Tag not found")
    return {"status": "deleted"}


# --- Tag Types ---


@router.get("/tag-types", response_model=list[TagTypeResponse])
async def list_tag_types(db: AsyncSession = DBDep) -> list[TagTypeResponse]:
    rows = await tag_service.get_tag_types(db)
    return [
        TagTypeResponse(
            id=tt.id, name=tt.name, label=tt.label,
            color=tt.color, sort_order=tt.sort_order, tag_count=count,
        )
        for tt, count in rows
    ]


@router.post("/tag-types", response_model=TagTypeResponse)
async def create_tag_type(
    data: TagTypeCreate, db: AsyncSession = DBDep
) -> TagTypeResponse:
    tt = await tag_service.create_tag_type(db, data)
    return TagTypeResponse(
        id=tt.id, name=tt.name, label=tt.label,
        color=tt.color, sort_order=tt.sort_order, tag_count=0,
    )


@router.put("/tag-types/{tt_id}", response_model=TagTypeResponse)
async def update_tag_type(
    tt_id: int, data: TagTypeUpdate, db: AsyncSession = DBDep
) -> TagTypeResponse:
    tt = await tag_service.update_tag_type(db, tt_id, data)
    if not tt:
        raise HTTPException(404, "Tag type not found")
    return TagTypeResponse(
        id=tt.id, name=tt.name, label=tt.label,
        color=tt.color, sort_order=tt.sort_order, tag_count=0,
    )


@router.delete("/tag-types/{tt_id}")
async def delete_tag_type(tt_id: int, db: AsyncSession = DBDep) -> dict[str, str]:
    deleted = await tag_service.delete_tag_type(db, tt_id)
    if not deleted:
        raise HTTPException(404, "Tag type not found")
    return {"status": "deleted"}
