"""AI 标签建议服务 — 使用 LLM 视觉能力分析图片并推荐标签。"""

import base64
import json
import logging

from app.ai.factory import get_llm_provider

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
你是图片标签分析助手。分析图片内容，生成描述性标签。
规则：
- 只返回 JSON 数组，每个元素格式: {"name": "标签名", "type": "类型", "confidence": 0-1}
- type 取值: general, character, meta
- 标签使用中文，角色名保留原文（可附中文翻译）
- 参考已有标签避免重复
- 每张图最多 15 个标签
- 不要添加任何解释文字，只返回 JSON 数组"""


async def suggest_tags(
    image_bytes: list[bytes] | None = None,
    existing_tags: list[str] | None = None,
    platform: str = "",
) -> list[dict]:
    """分析图片并建议标签。

    Returns:
        [{"name": str, "type": str, "confidence": float}] 按 confidence 降序
    """
    llm = get_llm_provider()
    if llm is None:
        return []

    # 将图片转为 base64
    image_b64: list[str] = []
    for data in image_bytes or []:
        image_b64.append(base64.b64encode(data).decode("ascii"))

    if not image_b64:
        return []

    context_parts = []
    if platform:
        context_parts.append(f"平台: {platform}")
    if existing_tags:
        context_parts.append(f"已有标签（请勿重复）: {', '.join(existing_tags)}")

    prompt = "请分析这张图片并推荐标签。"
    if context_parts:
        prompt += "\n" + "\n".join(context_parts)

    try:
        result = await llm.complete_with_images(prompt, image_b64=image_b64, system=SYSTEM_PROMPT)

        # 提取 JSON（LLM 可能在前后加了 markdown 代码块标记）
        result = result.strip()
        if result.startswith("```"):
            result = result.split("\n", 1)[-1].rsplit("```", 1)[0]
        result = result.strip()

        tags = json.loads(result)
        if not isinstance(tags, list):
            logger.warning("AI 标签返回非数组: %s", result[:200])
            return []

        # 过滤已有标签
        existing_set = {t.lower() for t in (existing_tags or [])}
        tags = [t for t in tags if t.get("name", "").lower() not in existing_set]

        # 确保结构正确并排序
        valid_tags = []
        for t in tags:
            if isinstance(t, dict) and "name" in t:
                valid_tags.append(
                    {
                        "name": t["name"],
                        "type": t.get("type", "general"),
                        "confidence": float(t.get("confidence", 0.5)),
                    }
                )
        valid_tags.sort(key=lambda x: x["confidence"], reverse=True)
        return valid_tags[:15]

    except json.JSONDecodeError:
        logger.warning("AI 标签 JSON 解析失败: %s", result[:200] if result else "empty")
        return []
    except Exception:
        logger.warning("AI 标签建议失败", exc_info=True)
        return []
