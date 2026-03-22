import io
import json

import imagehash
from fastapi import APIRouter, File, HTTPException, UploadFile
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.polisher import polish_title
from app.ai.search import compute_and_store_embedding, remove_embedding
from app.api.dependencies import AdminDep, CurrentUserDep, DBDep
from app.config import settings
from app.crawlers import crawl, try_extract_identity
from app.models.user import User
from app.schemas.artwork import (
    ArtworkAddSourceRequest,
    ArtworkCreate,
    ArtworkImportRequest,
    ArtworkMergeRequest,
    ArtworkResponse,
    ArtworkSourceResponse,
    ArtworkUpdate,
    ImportResponse,
    ReverseSearchResultSchema,
    SimilarArtworkInfo,
)
from app.schemas.author import AuthorCreate, AuthorResponse, AuthorUpdate
from app.schemas.tag import (
    TagCreate,
    TagResponse,
    TagTypeCreate,
    TagTypeResponse,
    TagTypeUpdate,
    TagUpdate,
)
from app.services import (
    artwork_service,
    author_service,
    queue_service,
    storage_service,
    tag_service,
)

router = APIRouter(dependencies=[AdminDep])


# --- 作者管理 ---


@router.post("/authors", response_model=AuthorResponse)
async def create_author(data: AuthorCreate, db: AsyncSession = DBDep) -> AuthorResponse:
    author = await author_service.create_author(db, data)
    return AuthorResponse.model_validate(author)


@router.put("/authors/{author_id}", response_model=AuthorResponse)
async def update_author(
    author_id: int, data: AuthorUpdate, db: AsyncSession = DBDep
) -> AuthorResponse:
    author = await author_service.update_author(db, author_id, data)
    if not author:
        raise HTTPException(404, "作者不存在")
    return AuthorResponse.model_validate(author)


@router.delete("/authors/{author_id}")
async def delete_author(author_id: int, db: AsyncSession = DBDep) -> dict[str, str]:
    deleted = await author_service.delete_author(db, author_id)
    if not deleted:
        raise HTTPException(404, "作者不存在")
    return {"status": "deleted"}


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
    # 先清理 embedding 缓存
    if settings.ai_embedding_enabled:
        await remove_embedding(db, artwork_id)
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
    data: ArtworkImportRequest,
    db: AsyncSession = DBDep,
    current_user: User | None = CurrentUserDep,
) -> ImportResponse:
    """抓取 URL，通过 platform+pid 和 pHash 去重，创建或合并。"""
    # 快速路径：若能从 URL 直接提取 identity，先查 DB，命中则跳过爬虫
    identity = try_extract_identity(data.url)
    if identity:
        platform, pid = identity
        cached = await artwork_service.get_artwork_by_pid(db, platform, pid)
        if cached:
            return ImportResponse(
                artwork=ArtworkResponse.model_validate(cached),
                message="已存在（缓存命中，跳过爬虫）。",
            )

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
    if current_user:
        artwork.imported_by_id = current_user.id
        await db.flush()
    await storage_service.download_and_store_images(db, artwork)

    # AI 标题润色
    if settings.ai_llm_enabled:
        title_zh = await polish_title(artwork.title, all_tags, artwork.platform)
        if title_zh:
            artwork.title_zh = title_zh
            await db.flush()

    await db.refresh(artwork)
    await db.refresh(artwork, attribute_names=["images", "tags", "sources"])

    # AI Embedding 计算
    if settings.ai_embedding_enabled:
        await compute_and_store_embedding(db, artwork)

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
                    similar.append(
                        SimilarArtworkInfo(
                            artwork_id=match_artwork.id,
                            distance=dist,
                            platform=match_artwork.platform,
                            pid=match_artwork.pid,
                            title=match_artwork.title,
                            thumb_url=thumb,
                        )
                    )

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
                            queued = False
                            if data.add_to_queue:
                                added_by = _queue_added_by(current_user)
                                await queue_service.add_to_queue(
                                    db, merged.id, priority=data.queue_priority, added_by=added_by
                                )
                                queued = True
                            return ImportResponse(
                                artwork=ArtworkResponse.model_validate(merged),
                                merged=True,
                                queued=queued,
                                message=(
                                    f"已自动合并到作品 #{target.artwork_id}"
                                    f"（pHash 匹配，距离={target.distance}）。"
                                ),
                            )
                    else:
                        # 将已有作品合并到新作品（新作品页数更多）
                        merged = await artwork_service.merge_artworks(
                            db, artwork.id, target.artwork_id
                        )
                        if merged:
                            queued = False
                            if data.add_to_queue:
                                added_by = _queue_added_by(current_user)
                                await queue_service.add_to_queue(
                                    db, merged.id, priority=data.queue_priority, added_by=added_by
                                )
                                queued = True
                            return ImportResponse(
                                artwork=ArtworkResponse.model_validate(merged),
                                merged=True,
                                queued=queued,
                                message=(
                                    f"已将作品 #{target.artwork_id} 合并到新作品"
                                    f" #{artwork.id}（页数更多）。"
                                ),
                            )

            if similar and not data.auto_merge:
                return ImportResponse(
                    artwork=ArtworkResponse.model_validate(artwork),
                    similar=similar,
                    message="发现相似作品。设置 auto_merge=true 可自动合并。",
                )

    queued = False
    if data.add_to_queue:
        added_by = _queue_added_by(current_user)
        await queue_service.add_to_queue(
            db, artwork.id, priority=data.queue_priority, added_by=added_by
        )
        queued = True
    return ImportResponse(
        artwork=ArtworkResponse.model_validate(artwork),
        queued=queued,
        message="已创建新作品。",
    )


# --- AI 批量润色 ---


@router.post("/artworks/polish-titles")
async def polish_titles(limit: int = 100, db: AsyncSession = DBDep) -> dict[str, int]:
    """批量润色缺少中文标题的作品。"""
    if not settings.ai_llm_enabled:
        raise HTTPException(400, "LLM 功能未启用")

    from sqlalchemy import select

    from app.models.artwork import Artwork

    stmt = select(Artwork).where(Artwork.title_zh == "", Artwork.title != "").limit(limit)
    result = await db.execute(stmt)
    artworks = list(result.scalars().all())

    polished = 0
    for aw in artworks:
        tag_names = [t.name for t in aw.tags]
        title_zh = await polish_title(aw.title, tag_names, aw.platform)
        if title_zh:
            aw.title_zh = title_zh
            polished += 1
    await db.commit()
    return {"total": len(artworks), "polished": polished}


# --- FTS 全文搜索 ---


@router.post("/fts/rebuild")
async def rebuild_fts(db: AsyncSession = DBDep) -> dict[str, int]:
    """重建全文搜索索引（SQLite FTS5）。"""
    from app.services.fts_service import rebuild_fts_index

    count = await rebuild_fts_index(db)
    return {"indexed": count}


# --- AI 标签建议 ---


@router.post("/artworks/{artwork_id}/suggest-tags")
async def suggest_tags_for_artwork(artwork_id: int, db: AsyncSession = DBDep) -> list[dict]:
    """使用 LLM 视觉分析作品图片并建议标签（不自动应用）。"""
    if not settings.ai_llm_enabled:
        raise HTTPException(400, "LLM 功能未启用")

    artwork = await artwork_service.get_artwork_by_id(db, artwork_id)
    if not artwork:
        raise HTTPException(404, "作品不存在")

    if not artwork.images:
        raise HTTPException(422, "作品没有图片")

    # 下载第一张图片
    first_image = sorted(artwork.images, key=lambda i: i.page_index)[0]
    image_url = first_image.url_original or first_image.url_thumb
    if not image_url:
        raise HTTPException(422, "无法获取图片 URL")

    image_data = await storage_service.download_image_bytes(image_url)
    existing_tags = [t.name for t in artwork.tags]

    from app.ai.tagger import suggest_tags

    return await suggest_tags(
        image_bytes=[image_data],
        existing_tags=existing_tags,
        platform=artwork.platform,
    )


@router.post("/artworks/batch-auto-tag")
async def batch_auto_tag(
    limit: int = 100, confidence: float = 0.8, db: AsyncSession = DBDep
) -> dict[str, int]:
    """批量为作品自动生成标签（仅添加高置信度标签）。"""
    if not settings.ai_llm_enabled:
        raise HTTPException(400, "LLM 功能未启用")

    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.ai.tagger import suggest_tags
    from app.models.artwork import Artwork

    stmt = (
        select(Artwork)
        .options(selectinload(Artwork.images), selectinload(Artwork.tags))
        .limit(limit)
    )
    result = await db.execute(stmt)
    artworks = list(result.scalars().all())

    tagged = 0
    for aw in artworks:
        if not aw.images:
            continue
        first_image = sorted(aw.images, key=lambda i: i.page_index)[0]
        image_url = first_image.url_original or first_image.url_thumb
        if not image_url:
            continue
        try:
            image_data = await storage_service.download_image_bytes(image_url)
        except Exception:
            continue

        existing = [t.name for t in aw.tags]
        suggestions = await suggest_tags(
            image_bytes=[image_data], existing_tags=existing, platform=aw.platform
        )
        new_tags = [s["name"] for s in suggestions if s["confidence"] >= confidence]
        if new_tags:
            from app.services.artwork_service import _get_or_create_tags

            tag_objs = await _get_or_create_tags(db, new_tags)
            for tag in tag_objs:
                if tag not in aw.tags:
                    aw.tags.append(tag)
            tagged += 1
    await db.commit()
    return {"total": len(artworks), "tagged": tagged}


# --- AI 批量 Embedding ---


@router.post("/artworks/compute-embeddings")
async def compute_embeddings(limit: int = 500, db: AsyncSession = DBDep) -> dict[str, int]:
    """为缺少 embedding 的作品批量计算并存储。"""
    if not settings.ai_embedding_enabled:
        raise HTTPException(400, "Embedding 功能未启用")

    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.models.artwork import Artwork, ArtworkEmbedding

    # 找出缺少 embedding 的作品
    subq = select(ArtworkEmbedding.artwork_id)
    stmt = (
        select(Artwork)
        .where(Artwork.id.notin_(subq))
        .options(selectinload(Artwork.tags))
        .limit(limit)
    )
    result = await db.execute(stmt)
    artworks = list(result.scalars().all())

    computed = 0
    for aw in artworks:
        ok = await compute_and_store_embedding(db, aw)
        if ok:
            computed += 1
    await db.commit()
    return {"total": len(artworks), "computed": computed}


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
            results.append(
                SimilarArtworkInfo(
                    artwork_id=artwork.id,
                    distance=dist,
                    platform=artwork.platform,
                    pid=artwork.pid,
                    title=artwork.title,
                    thumb_url=thumb,
                )
            )
    return results


# --- 以图搜图 (外部反向搜索) ---


@router.post("/artworks/reverse-search", response_model=list[ReverseSearchResultSchema])
async def reverse_search_image(
    file: UploadFile = File(...),
    min_similarity: float = 70.0,
) -> list[ReverseSearchResultSchema]:
    """上传图片，通过 SauceNAO / IQDB 反向搜索外部来源。"""
    from app.services.reverse_search_service import reverse_search

    data = await file.read()
    if not data:
        raise HTTPException(422, "未收到图片数据")

    results = await reverse_search(
        data,
        api_key=settings.saucenao_api_key,
        min_similarity=min_similarity,
    )
    return [
        ReverseSearchResultSchema(
            source_url=r.source_url,
            similarity=r.similarity,
            platform=r.platform,
            title=r.title,
            author=r.author,
            thumb_url=r.thumb_url,
            provider=r.provider,
        )
        for r in results
    ]


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
        raise HTTPException(
            409, f"来源 {result.platform}/{result.pid} 已关联到作品 #{existing.artwork_id}"
        )

    source = await artwork_service.add_source(
        db,
        artwork_id,
        result.platform,
        result.pid,
        result.source_url,
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


# --- 重复标签检测 ---


@router.get("/tags/duplicates")
async def get_duplicate_tags(threshold: float = 0.8, db: AsyncSession = DBDep) -> list[dict]:
    """检测相似度高于阈值的标签对。"""
    from app.services.tag_dedup_service import find_duplicate_tags

    return await find_duplicate_tags(db, threshold=threshold)


@router.post("/tags/merge")
async def merge_tags_endpoint(data: dict, db: AsyncSession = DBDep) -> dict[str, str]:
    """合并标签：将 merge_id 合并到 keep_id。"""
    keep_id = data.get("keep_id")
    merge_id = data.get("merge_id")
    if not keep_id or not merge_id:
        raise HTTPException(400, "需要 keep_id 和 merge_id")
    result = await tag_service.merge_tags(db, int(keep_id), int(merge_id))
    if not result:
        raise HTTPException(404, "标签不存在")
    await db.commit()
    return {"status": "merged"}


# --- 悬空图片清理 ---


@router.get("/cleanup/orphan-images")
async def get_orphan_images(db: AsyncSession = DBDep) -> list[dict]:
    """查找 storage_path 指向不存在文件的图片记录。"""
    from app.services.cleanup_service import find_orphan_images

    return await find_orphan_images(db)


@router.post("/cleanup/orphan-images")
async def cleanup_orphans(db: AsyncSession = DBDep) -> dict[str, int]:
    """清理悬空图片记录（清空 storage_path 以便重新下载）。"""
    from app.services.cleanup_service import cleanup_orphan_images

    count = await cleanup_orphan_images(db)
    return {"cleaned": count}


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
            id=tt.id,
            name=tt.name,
            label=tt.label,
            color=tt.color,
            sort_order=tt.sort_order,
            tag_count=count,
        )
        for tt, count in rows
    ]


@router.post("/tag-types", response_model=TagTypeResponse)
async def create_tag_type(data: TagTypeCreate, db: AsyncSession = DBDep) -> TagTypeResponse:
    tt = await tag_service.create_tag_type(db, data)
    return TagTypeResponse(
        id=tt.id,
        name=tt.name,
        label=tt.label,
        color=tt.color,
        sort_order=tt.sort_order,
        tag_count=0,
    )


@router.put("/tag-types/{tt_id}", response_model=TagTypeResponse)
async def update_tag_type(
    tt_id: int, data: TagTypeUpdate, db: AsyncSession = DBDep
) -> TagTypeResponse:
    tt = await tag_service.update_tag_type(db, tt_id, data)
    if not tt:
        raise HTTPException(404, "标签类型不存在")
    return TagTypeResponse(
        id=tt.id,
        name=tt.name,
        label=tt.label,
        color=tt.color,
        sort_order=tt.sort_order,
        tag_count=0,
    )


@router.delete("/tag-types/{tt_id}")
async def delete_tag_type(tt_id: int, db: AsyncSession = DBDep) -> dict[str, str]:
    deleted = await tag_service.delete_tag_type(db, tt_id)
    if not deleted:
        raise HTTPException(404, "标签类型不存在")
    return {"status": "deleted"}


def _queue_added_by(user: User | None) -> str:
    """生成队列条目的 added_by 字符串。"""
    if user is None:
        return "web_import"
    return getattr(user, "tg_username", None) or str(user.id)
