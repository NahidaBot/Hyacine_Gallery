from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import AdminDep, DBDep
from app.schemas.artwork import ArtworkCreate, ArtworkResponse, ImportResponse
from app.services import artwork_service

router = APIRouter(dependencies=[AdminDep])


@router.post("/artworks", response_model=ArtworkResponse)
async def create_artwork(
    data: ArtworkCreate,
    db: AsyncSession = DBDep,
) -> ArtworkResponse:
    from app.api.artworks import _to_response

    artwork = await artwork_service.create_artwork(db, data)
    return _to_response(artwork)


@router.delete("/artworks/{artwork_id}")
async def delete_artwork(artwork_id: int, db: AsyncSession = DBDep) -> dict[str, str]:
    deleted = await artwork_service.delete_artwork(db, artwork_id)
    if not deleted:
        raise HTTPException(404, "Artwork not found")
    return {"status": "deleted"}
