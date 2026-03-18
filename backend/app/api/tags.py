from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import DBDep
from app.schemas.common import TagCount
from app.services import artwork_service

router = APIRouter()


@router.get("", response_model=list[TagCount])
async def list_tags(db: AsyncSession = DBDep) -> list[TagCount]:
    tags = await artwork_service.get_tags_with_count(db)
    return [TagCount(tag=tag, count=count) for tag, count in tags]
