"""AI Provider 工厂 — 根据配置返回对应实例，模块级缓存单例。"""

import logging

from app.ai.providers import EmbeddingProvider, LLMProvider
from app.config import settings

logger = logging.getLogger(__name__)

_llm_instance: LLMProvider | None = None
_embedding_instance: EmbeddingProvider | None = None
_llm_initialized = False
_embedding_initialized = False


def get_llm_provider() -> LLMProvider | None:
    """获取 LLM Provider 单例，未启用时返回 None。"""
    global _llm_instance, _llm_initialized
    if _llm_initialized:
        return _llm_instance
    _llm_initialized = True

    if not settings.ai_llm_enabled:
        logger.info("LLM 功能未启用")
        return None

    from app.ai.llm_openai import OpenAILLMProvider

    _llm_instance = OpenAILLMProvider(
        base_url=settings.ai_llm_base_url,
        api_key=settings.ai_llm_api_key,
        model=settings.ai_llm_model,
    )
    logger.info("LLM Provider 已初始化: %s (%s)", settings.ai_llm_base_url, settings.ai_llm_model)
    return _llm_instance


def get_embedding_provider() -> EmbeddingProvider | None:
    """获取 Embedding Provider 单例，未启用时返回 None。"""
    global _embedding_instance, _embedding_initialized
    if _embedding_initialized:
        return _embedding_instance
    _embedding_initialized = True

    if not settings.ai_embedding_enabled:
        logger.info("Embedding 功能未启用")
        return None

    if settings.ai_embedding_provider == "api":
        from app.ai.embedding_api import APIEmbeddingProvider

        _embedding_instance = APIEmbeddingProvider(
            base_url=settings.ai_embedding_base_url,
            api_key=settings.ai_embedding_api_key,
            model=settings.ai_embedding_model,
            dim=settings.ai_embedding_dimension,
        )
        logger.info("Embedding Provider (API) 已初始化: %s", settings.ai_embedding_base_url)
    else:
        from app.ai.embedding_local import LocalEmbeddingProvider

        _embedding_instance = LocalEmbeddingProvider(
            model_name=settings.ai_embedding_model,
            dim=settings.ai_embedding_dimension,
        )
        logger.info("Embedding Provider (本地) 已初始化: %s", settings.ai_embedding_model)

    return _embedding_instance
