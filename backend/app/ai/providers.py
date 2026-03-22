"""AI Provider 抽象基类。"""

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """LLM 提供者抽象，用于标题润色等文本生成任务。"""

    @abstractmethod
    async def complete(self, prompt: str, system: str = "") -> str:
        """调用 LLM 生成文本。"""
        ...

    async def complete_with_images(
        self,
        prompt: str,
        image_b64: list[str] | None = None,
        system: str = "",
    ) -> str:
        """带图片的多模态调用。默认 fallback 到纯文本。"""
        return await self.complete(prompt, system=system)


class EmbeddingProvider(ABC):
    """Embedding 提供者抽象，用于语义搜索。"""

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """将文本列表转换为向量。"""
        ...

    @abstractmethod
    def dimension(self) -> int:
        """返回 embedding 维度。"""
        ...
