"""OpenAI 兼容 API 的 Embedding 实现。"""

import logging

import httpx

from app.ai.providers import EmbeddingProvider

logger = logging.getLogger(__name__)


class APIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, base_url: str, api_key: str, model: str, dim: int) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._dim = dim
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=60.0,
        )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        resp = await self._client.post(
            "/embeddings",
            json={"model": self._model, "input": texts},
        )
        resp.raise_for_status()
        data = resp.json()
        return [item["embedding"] for item in data["data"]]

    def dimension(self) -> int:
        return self._dim
