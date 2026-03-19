import io
import json

import imagehash
from fastapi import APIRouter, File, HTTPException, UploadFile
from PIL import Image
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


# --- 作品管理 ---


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
        raise HTTPException(404, "作品不存在")
    return ArtworkResponse.model_validate(artwork)


@router.delete("/artworks/{artwork_id}")
async def delete_artwork(artwork_id: int, db: AsyncSession = DBDep) -> dict[str, str]:
    deleted = await artwork_service.delete_artwork(db, artwork_id)
    if not deleted:
        raise HTTPException(404, "作品不存在")
    return {"status": "deleted"}


@router.delete("/artworks/{artwork_id}/images/{image_id}")
async def delete_artwork_image(
    artwork_id: int, image_id: int, db: AsyncSession = DBDep
) -> dict[str, str]:
    deleted = await artwork_service.delete_artwork_image(db, artwork_id, image_id)
    if not deleted:
        raise HTTPException(404, "图片不存在")
    return {"status": "deleted"}


@router.post("/artworks/import", response_model=ImportResponse)
async def import_artwork(
    data: ArtworkImportRequest, db: AsyncSession = DBDep
) -> ImportResponse:
    """抓取 URL，通过 platform+pid 和 pHash 去重，创建或合并。"""
    result = await crawl(data.url)
    if not result.success:
        raise HTTPException(422, f"抓取失败: {result.error}")

    # 第一步：同平台通过 artwork_sources 去重
    existing = await artwork_service.get_artwork_by_pid(db, result.platform, result.pid)
    if existing:
        return ImportResponse(
            artwork=ArtworkResponse.model_validate(existing),
            message="已存在（相同 platform+pid）。",
        )

    # 第二步：创建作品 + 下载图片（下载时计算 pHash）
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

    # 第三步：pHash 跨平台去重
    first_image = next((img for img in artwork.images if img.phash), None)
    if first_image and first_image.phash:
        matches = await artwork_service.find_similar_by_phash(db, first_image.phash)
        # 过滤掉刚创建的作品的匹配结果
        matches = [(img, dist) for img, dist in matches if img.artwork_id != artwork.id]

        if matches:
            # 按 artwork_id 分组，每个作品取最近的匹配
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
                # 自动合并：保留页数更多的
                target = similar[0]
                target_artwork = await artwork_service.get_artwork_by_id(db, target.artwork_id)
                if target_artwork:
                    if artwork.page_count <= target_artwork.page_count:
                        # 将新作品合并到已有作品（已有作品页数更多）
                        merged = await artwork_service.merge_artworks(
                            db, target.artwork_id, artwork.id
                        )
                        if merged:
                            return ImportResponse(
                                artwork=ArtworkResponse.model_validate(merged),
                                merged=True,
                                message=f"已自动合并到作品 #{target.artwork_id}（pHash 匹配，距离={target.distance}）。",
                            )
                    else:
                        # 将已有作品合并到新作品（新作品页数更多）
                        merged = await artwork_service.merge_artworks(
                            db, artwork.id, target.artwork_id
                        )
                        if merged:
                            return ImportResponse(
                                artwork=ArtworkResponse.model_validate(merged),
                                merged=True,
                                message=f"已将作品 #{target.artwork_id} 合并到新作品 #{artwork.id}（页数更多）。",
                            )

            if similar and not data.auto_merge:
                return ImportResponse(
                    artwork=ArtworkResponse.model_validate(artwork),
                    similar=similar,
                    message="发现相似作品。设置 auto_merge=true 可自动合并。",
                )

    return ImportResponse(
        artwork=ArtworkResponse.model_validate(artwork),
        message="已创建新作品。",
    )


# --- 以图搜图 (pHash) ---


@router.post("/artworks/search-by-image", response_model=list[SimilarArtworkInfo])
async def search_by_image(
    file: UploadFile = File(...),
    threshold: int = 10,
    db: AsyncSession = DBDep,
) -> list[SimilarArtworkInfo]:
    """上传图片，通过感知哈希查找相似作品。"""
    data = await file.read()
    try:
        img = Image.open(io.BytesIO(data))
        phash = str(imagehash.phash(img))
    except Exception as e:
        raise HTTPException(422, f"无法处理图片: {e}")

    matches = await artwork_service.find_similar_by_phash(db, phash, threshold=threshold)
    results: list[SimilarArtworkInfo] = []
    seen: set[int] = set()
    for img_record, dist in matches:
        if img_record.artwork_id in seen:
            continue
        seen.add(img_record.artwork_id)
        artwork = await artwork_service.get_artwork_by_id(db, img_record.artwork_id)
        if artwork:
            thumb = artwork.images[0].url_thumb if artwork.images else ""
            results.append(SimilarArtworkInfo(
                artwork_id=artwork.id,
                distance=dist,
                platform=artwork.platform,
                pid=artwork.pid,
                title=artwork.title,
                thumb_url=thumb,
            ))
    return results


# --- 作品来源 ---


@router.post("/artworks/{artwork_id}/sources", response_model=ArtworkSourceResponse)
async def add_artwork_source(
    artwork_id: int, data: ArtworkAddSourceRequest, db: AsyncSession = DBDep
) -> ArtworkSourceResponse:
    """抓取 URL 并作为来源添加到已有作品。"""
    artwork = await artwork_service.get_artwork_by_id(db, artwork_id)
    if not artwork:
        raise HTTPException(404, "作品不存在")

    result = await crawl(data.url)
    if not result.success:
        raise HTTPException(422, f"抓取失败: {result.error}")

    # 检查该来源是否已存在
    existing = await artwork_service.get_source_by_pid(db, result.platform, result.pid)
    if existing:
        raise HTTPException(409, f"来源 {result.platform}/{result.pid} 已关联到作品 #{existing.artwork_id}")

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
        raise HTTPException(404, "来源不存在或为主要来源")
    return {"status": "deleted"}


@router.post("/artworks/{artwork_id}/merge", response_model=ArtworkResponse)
async def merge_artwork(
    artwork_id: int, data: ArtworkMergeRequest, db: AsyncSession = DBDep
) -> ArtworkResponse:
    """将另一个作品合并到当前作品。"""
    if artwork_id == data.source_artwork_id:
        raise HTTPException(400, "不能将作品合并到自身")
    merged = await artwork_service.merge_artworks(db, artwork_id, data.source_artwork_id)
    if not merged:
        raise HTTPException(404, "作品不存在")
    return ArtworkResponse.model_validate(merged)


# --- 标签管理 ---


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
        raise HTTPException(404, "标签不存在")
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
        raise HTTPException(404, "标签不存在")
    return {"status": "deleted"}


# --- 标签类型 ---


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
        raise HTTPException(404, "标签类型不存在")
    return TagTypeResponse(
        id=tt.id, name=tt.name, label=tt.label,
        color=tt.color, sort_order=tt.sort_order, tag_count=0,
    )


@router.delete("/tag-types/{tt_id}")
async def delete_tag_type(tt_id: int, db: AsyncSession = DBDep) -> dict[str, str]:
    deleted = await tag_service.delete_tag_type(db, tt_id)
    if not deleted:
        raise HTTPException(404, "标签类型不存在")
    return {"status": "deleted"}
