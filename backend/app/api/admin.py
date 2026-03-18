from fastapi import APIRouter, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import AdminDep, DBDep
from app.schemas.artwork import ArtworkCreate, ArtworkResponse, ArtworkUpdate
from app.schemas.tag import TagCreate, TagResponse, TagUpdate
from app.services import artwork_service, tag_service

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
