from fastapi import APIRouter, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import DBDep
from app.schemas.artwork import ArtworkListResponse, ArtworkResponse
from app.schemas.tag import TagListResponse, TagResponse
from app.services import artwork_service, tag_service

router = APIRouter()


@router.get("", response_model=TagListResponse)
async def list_tags(
    db: AsyncSession = DBDep,
    type: str | None = None,
) -> TagListResponse:
    tags = await tag_service.get_tags(db, type_filter=type)
    data = [
        TagResponse(
            id=tag.id,
            name=tag.name,
            type=tag.type,
            alias_of_id=tag.alias_of_id,
            created_at=tag.created_at,
            artwork_count=count,
        )
        for tag, count in tags
    ]
    return TagListResponse(data=data, total=len(data))


@router.get("/{tag_name}", response_model=TagResponse)
async def get_tag(tag_name: str, db: AsyncSession = DBDep) -> TagResponse:
    tag = await tag_service.get_tag_by_name(db, tag_name)
    if not tag:
        raise HTTPException(404, "Tag not found")
    # Get artwork count for this tag
    tags_with_count = await tag_service.get_tags(db)
    count = next((c for t, c in tags_with_count if t.id == tag.id), 0)
    return TagResponse(
        id=tag.id,
        name=tag.name,
        type=tag.type,
        alias_of_id=tag.alias_of_id,
        created_at=tag.created_at,
        artwork_count=count,
    )


@router.get("/{tag_name}/artworks", response_model=ArtworkListResponse)
async def get_tag_artworks(
    tag_name: str,
    db: AsyncSession = DBDep,
    page: int = 1,
    page_size: int = 20,
) -> ArtworkListResponse:
    artworks, total = await artwork_service.get_artworks(
        db, page=page, page_size=page_size, tag=tag_name
    )
    return ArtworkListResponse(
        data=[ArtworkResponse.model_validate(a) for a in artworks],
        total=total,
        page=page,
        page_size=page_size,
    )
