from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import DBDep
from app.schemas.artwork import ArtworkListResponse, ArtworkResponse
from app.services import artwork_service

router = APIRouter()


def _to_response(artwork: object) -> ArtworkResponse:
    from app.models.artwork import Artwork

    assert isinstance(artwork, Artwork)
    return ArtworkResponse(
        id=artwork.id,
        platform=artwork.platform,
        pid=artwork.pid,
        title=artwork.title,
        author=artwork.author,
        author_id=artwork.author_id,
        source_url=artwork.source_url,
        page_count=artwork.page_count,
        width=artwork.width,
        height=artwork.height,
        is_nsfw=artwork.is_nsfw,
        is_ai=artwork.is_ai,
        images_json=artwork.images_json,
        tags=[t.tag for t in artwork.tags],
        created_at=artwork.created_at,
        updated_at=artwork.updated_at,
    )


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
        data=[_to_response(a) for a in artworks],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/random", response_model=ArtworkResponse)
async def random_artwork(db: AsyncSession = DBDep) -> ArtworkResponse:
    artwork = await artwork_service.get_random_artwork(db)
    if not artwork:
        raise HTTPException(404, "No artworks found")
    return _to_response(artwork)


@router.get("/{artwork_id}", response_model=ArtworkResponse)
async def get_artwork(artwork_id: int, db: AsyncSession = DBDep) -> ArtworkResponse:
    artwork = await artwork_service.get_artwork_by_id(db, artwork_id)
    if not artwork:
        raise HTTPException(404, "Artwork not found")
    return _to_response(artwork)
