"""重复标签检测 — 基于字符串相似度发现近似标签对。"""

import logging
from difflib import SequenceMatcher

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.artwork import Tag

logger = logging.getLogger(__name__)


def _similarity(a: str, b: str) -> float:
    """计算两个字符串的相似度 (0.0-1.0)。"""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


async def find_duplicate_tags(
    db: AsyncSession,
    threshold: float = 0.8,
) -> list[dict]:
    """找出相似度高于阈值的标签对。

    返回 [{"tag_a": {...}, "tag_b": {...}, "similarity": float}]
    排除已有 alias_of_id 关系的标签。
    """
    result = await db.execute(select(Tag).where(Tag.alias_of_id.is_(None)))
    tags = list(result.scalars().all())

    duplicates: list[dict] = []
    for i in range(len(tags)):
        for j in range(i + 1, len(tags)):
            a, b = tags[i], tags[j]
            # 长度差异过大时跳过
            if abs(len(a.name) - len(b.name)) > max(len(a.name), len(b.name)) * 0.5:
                continue
            sim = _similarity(a.name, b.name)
            if sim >= threshold:
                duplicates.append(
                    {
                        "tag_a": {"id": a.id, "name": a.name, "type": a.type},
                        "tag_b": {"id": b.id, "name": b.name, "type": b.type},
                        "similarity": round(sim, 3),
                    }
                )

    duplicates.sort(key=lambda d: d["similarity"], reverse=True)
    return duplicates
