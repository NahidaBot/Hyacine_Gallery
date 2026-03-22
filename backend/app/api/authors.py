from fastapi import APIRouter, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import DBDep
from app.schemas.artwork import ArtworkListResponse, ArtworkResponse
from app.schemas.author import AuthorCreate, AuthorResponse, AuthorUpdate
from app.services import author_service

router = APIRouter()


@router.get("", response_model=list[AuthorResponse])
async def list_authors(
    platform: str | None = None,
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = DBDep,
) -> list[AuthorResponse]:
    authors, _ = await author_service.list_authors(
        db, platform=platform, page=page, page_size=page_size
    )
    return [AuthorResponse.model_validate(a) for a in authors]


@router.get("/{author_id}", response_model=AuthorResponse)
async def get_author(author_id: int, db: AsyncSession = DBDep) -> AuthorResponse:
    author = await author_service.get_author(db, author_id)
    if not author:
        raise HTTPException(404, "作者不存在")
    return AuthorResponse.model_validate(author)


@router.get("/{author_id}/artworks", response_model=ArtworkListResponse)
async def get_author_artworks(
    author_id: int,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = DBDep,
) -> ArtworkListResponse:
    author = await author_service.get_author(db, author_id)
    if not author:
        raise HTTPException(404, "作者不存在")
    artworks, total = await author_service.get_artworks_by_author(
        db, author_id, page=page, page_size=page_size
    )
    return ArtworkListResponse(
        data=[ArtworkResponse.model_validate(a) for a in artworks],
        total=total,
        page=page,
        page_size=page_size,
    )


# --- 管理接口（需 AdminDep，在 admin router 中注册）---


async def admin_create_author(data: AuthorCreate, db: AsyncSession) -> AuthorResponse:
    author = await author_service.create_author(db, data)
    return AuthorResponse.model_validate(author)


async def admin_update_author(
    author_id: int, data: AuthorUpdate, db: AsyncSession
) -> AuthorResponse:
    author = await author_service.update_author(db, author_id, data)
    if not author:
        raise HTTPException(404, "作者不存在")
    return AuthorResponse.model_validate(author)


async def admin_delete_author(author_id: int, db: AsyncSession) -> dict[str, str]:
    deleted = await author_service.delete_author(db, author_id)
    if not deleted:
        raise HTTPException(404, "作者不存在")
    return {"status": "deleted"}
