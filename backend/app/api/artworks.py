from fastapi import APIRouter, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import DBDep
from app.schemas.artwork import ArtworkListResponse, ArtworkResponse
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


@router.get("/random", response_model=ArtworkResponse)
async def random_artwork(db: AsyncSession = DBDep) -> ArtworkResponse:
    artwork = await artwork_service.get_random_artwork(db)
    if not artwork:
        raise HTTPException(404, "No artworks found")
    return ArtworkResponse.model_validate(artwork)


@router.get("/{artwork_id}", response_model=ArtworkResponse)
async def get_artwork(artwork_id: int, db: AsyncSession = DBDep) -> ArtworkResponse:
    artwork = await artwork_service.get_artwork_by_id(db, artwork_id)
    if not artwork:
        raise HTTPException(404, "Artwork not found")
    return ArtworkResponse.model_validate(artwork)
