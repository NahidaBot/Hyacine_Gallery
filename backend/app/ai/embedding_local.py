"""本地 sentence-transformers Embedding 实现。

模型在首次调用时懒加载，需要安装可选依赖：
  uv pip install -e ".[ai]"
"""

import logging
from typing import Any

from app.ai.providers import EmbeddingProvider

logger = logging.getLogger(__name__)


class LocalEmbeddingProvider(EmbeddingProvider):
    def __init__(self, model_name: str, dim: int) -> None:
        self._model_name = model_name
        self._dim = dim
        self._model: Any = None

    def _load_model(self) -> Any:
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as e:
                msg = "本地 embedding 需要安装 sentence-transformers: uv pip install -e '.[ai]'"
                raise ImportError(msg) from e
            logger.info("加载本地 embedding 模型: %s", self._model_name)
            self._model = SentenceTransformer(self._model_name)
            logger.info("模型加载完成")
        return self._model

    async def embed(self, texts: list[str]) -> list[list[float]]:
        model = self._load_model()
        # sentence-transformers 是同步的，对于生产环境可考虑用 run_in_executor
        embeddings = model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()  # type: ignore[no-any-return]

    def dimension(self) -> int:
        return self._dim
