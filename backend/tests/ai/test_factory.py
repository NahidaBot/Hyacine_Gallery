"""AI Provider 工厂单元测试。"""

from unittest.mock import MagicMock, patch

import app.ai.factory as factory_module


def _reset_factory_cache():
    """重置工厂模块的单例缓存。"""
    factory_module._llm_instance = None
    factory_module._embedding_instance = None
    factory_module._llm_initialized = False
    factory_module._embedding_initialized = False


class TestGetLLMProvider:
    def test_get_llm_provider_disabled(self, monkeypatch):
        """ai_llm_enabled=False 时返回 None。"""
        _reset_factory_cache()
        monkeypatch.setattr(factory_module.settings, "ai_llm_enabled", False)

        result = factory_module.get_llm_provider()
        assert result is None

    def test_get_llm_provider_enabled(self, monkeypatch):
        """ai_llm_enabled=True 时返回 provider 实例。"""
        _reset_factory_cache()
        monkeypatch.setattr(factory_module.settings, "ai_llm_enabled", True)
        monkeypatch.setattr(factory_module.settings, "ai_llm_base_url", "http://test-llm")
        monkeypatch.setattr(factory_module.settings, "ai_llm_api_key", "test-key")
        monkeypatch.setattr(factory_module.settings, "ai_llm_model", "test-model")

        mock_provider = MagicMock()
        mock_cls = MagicMock(return_value=mock_provider)
        fake_module = MagicMock(OpenAILLMProvider=mock_cls)

        with patch.dict("sys.modules", {"app.ai.llm_openai": fake_module}):
            result = factory_module.get_llm_provider()

        assert result is mock_provider
        mock_cls.assert_called_once_with(
            base_url="http://test-llm",
            api_key="test-key",
            model="test-model",
        )


class TestGetEmbeddingProvider:
    def test_get_embedding_provider_disabled(self, monkeypatch):
        """ai_embedding_enabled=False 时返回 None。"""
        _reset_factory_cache()
        monkeypatch.setattr(factory_module.settings, "ai_embedding_enabled", False)

        result = factory_module.get_embedding_provider()
        assert result is None

    def test_get_embedding_provider_api(self, monkeypatch):
        """ai_embedding_provider='api' 时返回 API provider。"""
        _reset_factory_cache()
        monkeypatch.setattr(factory_module.settings, "ai_embedding_enabled", True)
        monkeypatch.setattr(factory_module.settings, "ai_embedding_provider", "api")
        monkeypatch.setattr(factory_module.settings, "ai_embedding_base_url", "http://test-embed")
        monkeypatch.setattr(factory_module.settings, "ai_embedding_api_key", "test-key")
        monkeypatch.setattr(factory_module.settings, "ai_embedding_model", "test-model")
        monkeypatch.setattr(factory_module.settings, "ai_embedding_dimension", 128)

        mock_provider = MagicMock()
        mock_cls = MagicMock(return_value=mock_provider)
        fake_module = MagicMock(APIEmbeddingProvider=mock_cls)

        with patch.dict("sys.modules", {"app.ai.embedding_api": fake_module}):
            result = factory_module.get_embedding_provider()

        assert result is mock_provider
        mock_cls.assert_called_once_with(
            base_url="http://test-embed",
            api_key="test-key",
            model="test-model",
            dim=128,
        )
