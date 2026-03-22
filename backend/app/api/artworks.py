from fastapi import APIRouter, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import DBDep
from app.config import settings
from app.schemas.artwork import (
    ArtworkListResponse,
    ArtworkResponse,
    SemanticSearchResponse,
    SemanticSearchResult,
)
from app.services import artwork_service

router = APIRouter()


@router.get("", response_model=ArtworkListResponse)
async def list_artworks(
    db: AsyncSession = DBDep,
    page: int = 1,
    page_size: int = 20,
    platform: str | None = None,
    tag: str | None = None,
    q: str | None = None,
) -> ArtworkListResponse:
    artworks, total = await artwork_service.get_artworks(
        db, page=page, page_size=page_size, platform=platform, tag=tag, q=q
    )
    return ArtworkListResponse(
        data=[ArtworkResponse.model_validate(a) for a in artworks],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/search", response_model=SemanticSearchResponse)
async def search_artworks(
    q: str,
    top_k: int = 10,
    db: AsyncSession = DBDep,
) -> SemanticSearchResponse:
    """语义搜索。若 embedding 未启用则 fallback 到关键词搜索。"""
    if settings.ai_embedding_enabled:
        from app.ai.search import semantic_search

        matches = await semantic_search(db, q, top_k=top_k)
        results: list[SemanticSearchResult] = []
        for artwork_id, score in matches:
            artwork = await artwork_service.get_artwork_by_id(db, artwork_id)
            if artwork:
                results.append(
                    SemanticSearchResult(
                        artwork=ArtworkResponse.model_validate(artwork),
                        score=score,
                    )
                )
        return SemanticSearchResponse(results=results, query=q)

    # Fallback: 关键词搜索
    artworks, _ = await artwork_service.get_artworks(db, page=1, page_size=top_k, q=q)
    return SemanticSearchResponse(
        results=[
            SemanticSearchResult(artwork=ArtworkResponse.model_validate(a), score=1.0)
            for a in artworks
        ],
        query=q,
    )


@router.get("/random", response_model=ArtworkResponse)
async def random_artwork(db: AsyncSession = DBDep) -> ArtworkResponse:
    artwork = await artwork_service.get_random_artwork(db)
    if not artwork:
        raise HTTPException(404, "暂无作品")
    return ArtworkResponse.model_validate(artwork)


@router.get("/{artwork_id}", response_model=ArtworkResponse)
async def get_artwork(artwork_id: int, db: AsyncSession = DBDep) -> ArtworkResponse:
    artwork = await artwork_service.get_artwork_by_id(db, artwork_id)
    if not artwork:
        raise HTTPException(404, "作品不存在")
    return ArtworkResponse.model_validate(artwork)
