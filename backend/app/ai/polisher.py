"""标题润色服务 — 调用 LLM 将日/英文标题翻译为中文。"""

import logging
import unicodedata

from app.ai.factory import get_llm_provider

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
你是一个图片标题翻译助手。将给定的图片标题翻译为简洁自然的简体中文。
规则：
- 只输出翻译后的标题，不要任何解释或额外文字
- 保留人名、作品名等专有名词的原文（可在括号内附中文）
- 如果标题包含 emoji 或特殊符号，保留它们
- 翻译应简洁优雅，避免生硬直译
- 如果标题本身无实际含义（如纯符号、编号），直接原样返回"""


def _is_mostly_chinese(text: str, threshold: float = 0.5) -> bool:
    """判断文本是否主要由中文字符组成。"""
    if not text:
        return False
    cjk_count = sum(1 for ch in text if unicodedata.category(ch).startswith("Lo"))
    alpha_count = sum(1 for ch in text if unicodedata.category(ch).startswith(("L",)))
    if alpha_count == 0:
        return False
    return cjk_count / alpha_count > threshold


async def polish_title(title: str, tags: list[str], platform: str) -> str | None:
    """将标题翻译为中文。返回翻译结果，跳过时返回 None。

    Args:
        title: 原始标题
        tags: 作品标签列表（提供上下文）
        platform: 来源平台
    """
    if not title or _is_mostly_chinese(title):
        return None

    llm = get_llm_provider()
    if llm is None:
        return None

    context_parts = [f"平台: {platform}"]
    if tags:
        context_parts.append(f"标签: {', '.join(tags[:15])}")

    prompt = f"标题: {title}\n{chr(10).join(context_parts)}"

    try:
        result = await llm.complete(prompt, system=SYSTEM_PROMPT)
        # 去掉 LLM 可能添加的引号
        result = result.strip().strip("\"'「」『』")
        if result:
            logger.info("标题润色: %s → %s", title, result)
            return result
    except Exception:
        logger.warning("标题润色失败: %s", title, exc_info=True)

    return None
