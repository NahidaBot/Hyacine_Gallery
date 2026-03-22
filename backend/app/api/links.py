from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import AdminDep, DBDep
from app.models.site import FriendLink
from app.schemas.site import FriendLinkCreate, FriendLinkResponse, FriendLinkUpdate

# 公开路由
public_router = APIRouter()

# 管理路由（需要鉴权）
admin_router = APIRouter(dependencies=[AdminDep])


@public_router.get("", response_model=list[FriendLinkResponse])
async def list_links(db: AsyncSession = DBDep) -> list[FriendLinkResponse]:
    """公开接口：列出所有已启用的友情链接，按 sort_order 排序。"""
    result = await db.execute(
        select(FriendLink)
        .where(FriendLink.enabled == True)  # noqa: E712
        .order_by(FriendLink.sort_order, FriendLink.id)
    )
    links = result.scalars().all()
    return [FriendLinkResponse.model_validate(lk) for lk in links]


@admin_router.get("/links", response_model=list[FriendLinkResponse])
async def admin_list_links(db: AsyncSession = DBDep) -> list[FriendLinkResponse]:
    """管理接口：列出所有友情链接（含禁用）。"""
    result = await db.execute(
        select(FriendLink).order_by(FriendLink.sort_order, FriendLink.id)
    )
    links = result.scalars().all()
    return [FriendLinkResponse.model_validate(lk) for lk in links]


@admin_router.post("/links", response_model=FriendLinkResponse)
async def create_link(data: FriendLinkCreate, db: AsyncSession = DBDep) -> FriendLinkResponse:
    link = FriendLink(**data.model_dump())
    db.add(link)
    await db.commit()
    await db.refresh(link)
    return FriendLinkResponse.model_validate(link)


@admin_router.put("/links/{link_id}", response_model=FriendLinkResponse)
async def update_link(
    link_id: int, data: FriendLinkUpdate, db: AsyncSession = DBDep
) -> FriendLinkResponse:
    link = await db.get(FriendLink, link_id)
    if not link:
        raise HTTPException(404, "友情链接不存在")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(link, field, value)
    await db.commit()
    await db.refresh(link)
    return FriendLinkResponse.model_validate(link)


@admin_router.delete("/links/{link_id}")
async def delete_link(link_id: int, db: AsyncSession = DBDep) -> dict[str, str]:
    link = await db.get(FriendLink, link_id)
    if not link:
        raise HTTPException(404, "友情链接不存在")
    await db.delete(link)
    await db.commit()
    return {"message": "已删除"}
