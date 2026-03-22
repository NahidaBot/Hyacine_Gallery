"""NSFW 自动检测 — LLM 视觉 + 本地模型双模式。"""

import base64
import logging
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

_local_classifier: Any = None


async def detect_nsfw(image_bytes: bytes) -> float:
    """检测图片 NSFW 程度，返回 0.0-1.0 的分数。"""
    provider = settings.nsfw_detection_provider
    if provider == "llm":
        return await _detect_nsfw_llm(image_bytes)
    elif provider == "local":
        return _detect_nsfw_local(image_bytes)
    else:
        logger.warning("未知的 NSFW 检测模式: %s", provider)
        return 0.0


async def _detect_nsfw_llm(image_bytes: bytes) -> float:
    """使用 LLM 视觉模型判断 NSFW 程度。"""
    from app.ai.factory import get_llm_provider

    llm = get_llm_provider()
    if llm is None:
        return 0.0

    b64 = base64.b64encode(image_bytes).decode("ascii")
    prompt = (
        "判断这张图片的 NSFW 程度。"
        "只回复一个 0.0 到 1.0 之间的数字，不要其他文字。"
        "0.0=完全安全，0.5=略有暴露，1.0=明确 NSFW。"
    )

    try:
        result = await llm.complete_with_images(prompt, image_b64=[b64])
        # 提取数字
        result = result.strip()
        score = float(result.replace(",", "."))
        return max(0.0, min(1.0, score))
    except ValueError, TypeError:
        logger.warning("NSFW LLM 返回非数字: %s", result[:50] if result else "empty")
        return 0.0
    except Exception:
        logger.warning("NSFW LLM 检测失败", exc_info=True)
        return 0.0


def _detect_nsfw_local(image_bytes: bytes) -> float:
    """使用本地 transformers 模型检测 NSFW。"""
    global _local_classifier

    if _local_classifier is None:
        try:
            from transformers import pipeline
        except ImportError as e:
            msg = "本地 NSFW 检测需要安装 transformers: uv pip install -e '.[ai]'"
            raise ImportError(msg) from e

        logger.info("加载本地 NSFW 检测模型...")
        _local_classifier = pipeline(
            "image-classification",
            model="Falconsai/nsfw_image_detection",
        )
        logger.info("NSFW 模型加载完成")

    import io

    from PIL import Image

    img = Image.open(io.BytesIO(image_bytes))
    results = _local_classifier(img)

    # 返回 nsfw 标签的分数
    for r in results:
        if r["label"].lower() == "nsfw":
            return float(r["score"])
    return 0.0
