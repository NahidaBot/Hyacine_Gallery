"""OpenAI 兼容 API 的 LLM 实现。

通过 base_url 切换后端：
- OpenAI: https://api.openai.com/v1
- Ollama: http://localhost:11434/v1
- 其他兼容服务
"""

import logging

import httpx

from app.ai.providers import LLMProvider

logger = logging.getLogger(__name__)


class OpenAILLMProvider(LLMProvider):
    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={"Authorization": f"Bearer {self._api_key}"},
            timeout=30.0,
        )

    async def complete(self, prompt: str, system: str = "") -> str:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        resp = await self._client.post(
            "/chat/completions",
            json={"model": self._model, "messages": messages, "temperature": 0.3},
        )
        resp.raise_for_status()
        data = resp.json()
        return str(data["choices"][0]["message"]["content"]).strip()

    async def complete_with_images(
        self,
        prompt: str,
        image_b64: list[str] | None = None,
        system: str = "",
    ) -> str:
        """构建 OpenAI multimodal messages 格式。"""
        messages: list[dict[str, object]] = []
        if system:
            messages.append({"role": "system", "content": system})

        content: list[dict[str, object]] = [{"type": "text", "text": prompt}]
        for b64 in image_b64 or []:
            content.append(
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
            )
        messages.append({"role": "user", "content": content})

        resp = await self._client.post(
            "/chat/completions",
            json={"model": self._model, "messages": messages, "temperature": 0.3},
        )
        resp.raise_for_status()
        data = resp.json()
        return str(data["choices"][0]["message"]["content"]).strip()
